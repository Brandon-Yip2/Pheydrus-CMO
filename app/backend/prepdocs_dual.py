"""
Config-driven document preparation script for dual-CMO system.

This script reads from data/index_config.json to determine which folders
should be indexed into which search index (private/internal vs public).

Usage:
    python prepdocs_dual.py [--index private|public|both] [--verbose]

    --index: Which index to process (default: both)
    --verbose: Enable verbose logging
"""

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Union

import aiohttp
from azure.core.credentials import AzureKeyCredential
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import AzureDeveloperCliCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI, AsyncOpenAI
from rich.logging import RichHandler

from load_azd_env import load_azd_env
from prepdocslib.blobmanager import BlobManager
from prepdocslib.csvparser import CsvParser
from prepdocslib.embeddings import (
    AzureOpenAIEmbeddingService,
    ImageEmbeddings,
    OpenAIEmbeddingService,
)
from prepdocslib.fileprocessor import FileProcessor
from prepdocslib.filestrategy import FileStrategy
from prepdocslib.htmlparser import LocalHTMLParser
from prepdocslib.integratedvectorizerstrategy import IntegratedVectorizerStrategy
from prepdocslib.jsonparser import JsonParser
from prepdocslib.listfilestrategy import (
    ADLSGen2ListFileStrategy,
    ListFileStrategy,
    LocalListFileStrategy,
)
from prepdocslib.parser import Parser
from prepdocslib.pdfparser import (
    DocumentAnalysisParser,
    LocalPdfParser,
    MediaDescriptionStrategy,
)
from prepdocslib.strategy import DocumentAction, SearchInfo, Strategy
from prepdocslib.textparser import TextParser
from prepdocslib.textsplitter import SentenceTextSplitter, SimpleTextSplitter

# Import the config system
from core.index_config import (
    load_index_config,
    get_folders_for_index,
    get_index_name,
    IndexConfigError,
)
from prepdocs import (
    OpenAIHost,
    clean_key_if_exists,
    check_search_service_connectivity,
    setup_search_info,
    setup_blob_manager,
    setup_embeddings_service,
    setup_openai_client,
    setup_file_processors,
    setup_image_embeddings_service,
    main,
)

logger = logging.getLogger("scripts")


def get_project_root() -> Path:
    """Get the project root directory (where data/ folder is located)."""
    # This script is in app/backend/, so project root is 2 levels up
    return Path(__file__).parent.parent.parent


def get_config_path() -> Path:
    """Get the path to index_config.json."""
    return get_project_root() / "data" / "index_config.json"


def get_folders_to_process(index_type: str) -> list[str]:
    """
    Get list of folder paths to process for the given index type.

    Args:
        index_type: Either 'private' or 'public'

    Returns:
        List of absolute folder paths to process
    """
    config_path = get_config_path()
    config = load_index_config(str(config_path))

    relative_folders = get_folders_for_index(config, index_type)
    project_root = get_project_root()

    absolute_folders = []
    for folder in relative_folders:
        abs_path = project_root / folder
        if abs_path.exists():
            absolute_folders.append(str(abs_path))
        else:
            logger.warning(f"Folder does not exist: {abs_path}")

    return absolute_folders


def create_file_pattern_for_folders(folders: list[str]) -> str:
    """
    Create a glob pattern that matches files in the given folders.

    Since LocalListFileStrategy uses glob patterns, we need to construct
    appropriate patterns for each folder.
    """
    # For a single folder, return pattern matching all files in it
    # For multiple folders, we'll need to process them separately
    if len(folders) == 1:
        return f"{folders[0]}/**/*"
    return None  # Will need special handling for multiple folders


async def process_index(
    index_type: str,
    azd_credential: AsyncTokenCredential,
    args: argparse.Namespace,
    document_action: DocumentAction,
) -> bool:
    """
    Process documents for a specific index (private or public).

    Args:
        index_type: 'private' or 'public'
        azd_credential: Azure credential for authentication
        args: Command line arguments
        document_action: Add, Remove, or RemoveAll

    Returns:
        True if processing was successful, False otherwise
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing {index_type.upper()} CMO index")
    logger.info(f"{'='*60}")

    # Get the index name from environment
    if index_type == "private":
        index_name = os.getenv("AZURE_SEARCH_INDEX_INTERNAL", os.environ.get("AZURE_SEARCH_INDEX", "gptkbindex-internal"))
    else:
        index_name = os.getenv("AZURE_SEARCH_INDEX_PUBLIC", "gptkbindex-public")

    logger.info(f"Target index: {index_name}")

    # Get folders to process
    folders = get_folders_to_process(index_type)

    if not folders:
        logger.warning(f"No folders configured for {index_type} index")
        return True

    logger.info(f"Folders to process: {folders}")

    # Check search service connectivity
    search_service = os.environ["AZURE_SEARCH_SERVICE"]
    is_connected = await check_search_service_connectivity(search_service)

    if not is_connected:
        if os.getenv("AZURE_USE_PRIVATE_ENDPOINT"):
            logger.error(
                "Unable to connect to Azure AI Search service. You have AZURE_USE_PRIVATE_ENDPOINT enabled. "
                "Perhaps you're not yet connected to the VPN?"
            )
        else:
            logger.error("Unable to connect to Azure AI Search service.")
        return False

    # Setup configuration
    use_int_vectorization = os.getenv("USE_FEATURE_INT_VECTORIZATION", "").lower() == "true"
    use_multimodal = os.getenv("USE_MULTIMODAL", "").lower() == "true"
    use_acls = os.getenv("AZURE_ENFORCE_ACCESS_CONTROL") is not None
    dont_use_vectors = os.getenv("USE_VECTORS", "").lower() == "false"
    use_agentic_retrieval = os.getenv("USE_AGENTIC_RETRIEVAL", "").lower() == "true"
    use_content_understanding = os.getenv("USE_MEDIA_DESCRIBER_AZURE_CU", "").lower() == "true"

    OPENAI_HOST = OpenAIHost(os.environ["OPENAI_HOST"])

    if use_agentic_retrieval and OPENAI_HOST not in [OpenAIHost.AZURE, OpenAIHost.AZURE_CUSTOM]:
        raise Exception("Agentic retrieval requires an Azure OpenAI chat completion service")

    # Setup search info for this index
    search_info = await setup_search_info(
        search_service=os.environ["AZURE_SEARCH_SERVICE"],
        index_name=index_name,
        use_agentic_retrieval=use_agentic_retrieval,
        agent_name=os.getenv("AZURE_SEARCH_AGENT"),
        agent_max_output_tokens=int(os.getenv("AZURE_SEARCH_AGENT_MAX_OUTPUT_TOKENS", 10000)),
        azure_openai_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_openai_searchagent_deployment=os.getenv("AZURE_OPENAI_SEARCHAGENT_DEPLOYMENT"),
        azure_openai_searchagent_model=os.getenv("AZURE_OPENAI_SEARCHAGENT_MODEL"),
        azure_credential=azd_credential,
        search_key=clean_key_if_exists(args.searchkey) if hasattr(args, 'searchkey') else None,
        azure_vision_endpoint=os.getenv("AZURE_VISION_ENDPOINT"),
    )

    # Setup blob manager
    blob_manager = setup_blob_manager(
        azure_credential=azd_credential,
        storage_account=os.environ["AZURE_STORAGE_ACCOUNT"],
        storage_container=os.environ["AZURE_STORAGE_CONTAINER"],
        storage_resource_group=os.environ["AZURE_STORAGE_RESOURCE_GROUP"],
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
        storage_key=clean_key_if_exists(args.storagekey) if hasattr(args, 'storagekey') else None,
        image_storage_container=os.environ.get("AZURE_IMAGESTORAGE_CONTAINER"),
    )

    # Setup embeddings
    azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION") or "2024-06-01"
    emb_model_dimensions = 1536
    if os.getenv("AZURE_OPENAI_EMB_DIMENSIONS"):
        emb_model_dimensions = int(os.environ["AZURE_OPENAI_EMB_DIMENSIONS"])

    openai_embeddings_service = setup_embeddings_service(
        azure_credential=azd_credential,
        openai_host=OPENAI_HOST,
        emb_model_name=os.environ["AZURE_OPENAI_EMB_MODEL_NAME"],
        emb_model_dimensions=emb_model_dimensions,
        azure_openai_service=os.getenv("AZURE_OPENAI_SERVICE"),
        azure_openai_custom_url=os.getenv("AZURE_OPENAI_CUSTOM_URL"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT"),
        azure_openai_api_version=azure_openai_api_version,
        azure_openai_key=os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE"),
        openai_key=clean_key_if_exists(os.getenv("OPENAI_API_KEY")),
        openai_org=os.getenv("OPENAI_ORGANIZATION"),
        disable_vectors=dont_use_vectors,
        disable_batch_vectors=args.disablebatchvectors if hasattr(args, 'disablebatchvectors') else False,
    )

    openai_client = setup_openai_client(
        openai_host=OPENAI_HOST,
        azure_credential=azd_credential,
        azure_openai_api_version=azure_openai_api_version,
        azure_openai_service=os.getenv("AZURE_OPENAI_SERVICE"),
        azure_openai_custom_url=os.getenv("AZURE_OPENAI_CUSTOM_URL"),
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY_OVERRIDE"),
        openai_api_key=clean_key_if_exists(os.getenv("OPENAI_API_KEY")),
        openai_organization=os.getenv("OPENAI_ORGANIZATION"),
    )

    # Process each folder separately
    success = True
    for folder in folders:
        logger.info(f"\nProcessing folder: {folder}")

        # Create file pattern for this folder
        file_pattern = f"{folder}/**/*"

        list_file_strategy = LocalListFileStrategy(path_pattern=file_pattern)

        # Setup ingestion strategy
        if use_int_vectorization:
            if not openai_embeddings_service or not isinstance(openai_embeddings_service, AzureOpenAIEmbeddingService):
                raise Exception("Integrated vectorization strategy requires an Azure OpenAI embeddings service")

            ingestion_strategy = IntegratedVectorizerStrategy(
                search_info=search_info,
                list_file_strategy=list_file_strategy,
                blob_manager=blob_manager,
                document_action=document_action,
                embeddings=openai_embeddings_service,
                search_field_name_embedding=os.environ["AZURE_SEARCH_FIELD_NAME_EMBEDDING"],
                subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
                search_analyzer_name=os.getenv("AZURE_SEARCH_ANALYZER_NAME"),
                use_acls=use_acls,
                category=args.category if hasattr(args, 'category') else None,
            )
        else:
            file_processors = setup_file_processors(
                azure_credential=azd_credential,
                document_intelligence_service=os.getenv("AZURE_DOCUMENTINTELLIGENCE_SERVICE"),
                document_intelligence_key=clean_key_if_exists(args.documentintelligencekey) if hasattr(args, 'documentintelligencekey') else None,
                local_pdf_parser=os.getenv("USE_LOCAL_PDF_PARSER") == "true",
                local_html_parser=os.getenv("USE_LOCAL_HTML_PARSER") == "true",
                use_content_understanding=use_content_understanding,
                use_multimodal=use_multimodal,
                content_understanding_endpoint=os.getenv("AZURE_CONTENTUNDERSTANDING_ENDPOINT"),
                openai_client=openai_client,
                openai_model=os.getenv("AZURE_OPENAI_CHATGPT_MODEL"),
                openai_deployment=os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT") if OPENAI_HOST == OpenAIHost.AZURE else None,
            )

            image_embeddings_service = setup_image_embeddings_service(
                azure_credential=azd_credential,
                vision_endpoint=os.getenv("AZURE_VISION_ENDPOINT"),
                use_multimodal=use_multimodal,
            )

            ingestion_strategy = FileStrategy(
                search_info=search_info,
                list_file_strategy=list_file_strategy,
                blob_manager=blob_manager,
                file_processors=file_processors,
                document_action=document_action,
                embeddings=openai_embeddings_service,
                image_embeddings=image_embeddings_service,
                search_analyzer_name=os.getenv("AZURE_SEARCH_ANALYZER_NAME"),
                search_field_name_embedding=os.getenv("AZURE_SEARCH_FIELD_NAME_EMBEDDING", "embedding"),
                use_acls=use_acls,
                category=args.category if hasattr(args, 'category') else None,
                use_content_understanding=use_content_understanding,
                content_understanding_endpoint=os.getenv("AZURE_CONTENTUNDERSTANDING_ENDPOINT"),
            )

        try:
            setup_index = document_action == DocumentAction.Add
            await main(ingestion_strategy, setup_index=setup_index)
            logger.info(f"Successfully processed folder: {folder}")
        except Exception as e:
            logger.error(f"Error processing folder {folder}: {e}")
            success = False

    # Cleanup
    try:
        await blob_manager.close_clients()
        await openai_client.close()
    except Exception as e:
        logger.debug(f"Failed to close async clients cleanly: {e}")

    return success


async def run_dual_indexing(args: argparse.Namespace):
    """
    Main entry point for dual-index document processing.
    """
    load_azd_env()

    if (
        os.getenv("AZURE_PUBLIC_NETWORK_ACCESS") == "Disabled"
        and os.getenv("AZURE_USE_VPN_GATEWAY", "").lower() != "true"
    ):
        logger.error("AZURE_PUBLIC_NETWORK_ACCESS is set to Disabled. Exiting.")
        return

    # Load and validate config
    config_path = get_config_path()
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        logger.error("Please create data/index_config.json with folder-to-index mappings.")
        return

    try:
        config = load_index_config(str(config_path))
        logger.info(f"Loaded config from: {config_path}")
        logger.info(f"Config version: {config.get('version', 'unknown')}")
    except IndexConfigError as e:
        logger.error(f"Invalid config: {e}")
        return

    # Setup Azure credential
    if tenant_id := os.getenv("AZURE_TENANT_ID"):
        logger.info("Connecting to Azure services using the azd credential for tenant %s", tenant_id)
        azd_credential = AzureDeveloperCliCredential(tenant_id=tenant_id, process_timeout=60)
    else:
        logger.info("Connecting to Azure services using the azd credential for home tenant")
        azd_credential = AzureDeveloperCliCredential(process_timeout=60)

    # Determine document action
    if args.removeall:
        document_action = DocumentAction.RemoveAll
    elif args.remove:
        document_action = DocumentAction.Remove
    else:
        document_action = DocumentAction.Add

    # Process indexes based on --index argument
    indexes_to_process = []
    if args.index == "both":
        indexes_to_process = ["private", "public"]
    else:
        indexes_to_process = [args.index]

    logger.info(f"Document action: {document_action}")
    logger.info(f"Indexes to process: {indexes_to_process}")

    all_success = True
    for index_type in indexes_to_process:
        success = await process_index(
            index_type=index_type,
            azd_credential=azd_credential,
            args=args,
            document_action=document_action,
        )
        if not success:
            all_success = False

    # Cleanup credential
    try:
        await azd_credential.close()
    except Exception as e:
        logger.debug(f"Failed to close credential: {e}")

    if all_success:
        logger.info("\n" + "="*60)
        logger.info("All indexes processed successfully!")
        logger.info("="*60)
    else:
        logger.error("\n" + "="*60)
        logger.error("Some indexes failed to process. Check logs above.")
        logger.error("="*60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Config-driven document preparation for dual-CMO system. "
                    "Reads data/index_config.json to determine which folders go to which search index."
    )

    parser.add_argument(
        "--index",
        choices=["private", "public", "both"],
        default="both",
        help="Which index to process (default: both)"
    )

    parser.add_argument(
        "--category",
        help="Value for the category field in the search index for all sections indexed in this run"
    )

    parser.add_argument(
        "--skipblobs",
        action="store_true",
        help="Skip uploading individual pages to Azure Blob Storage"
    )

    parser.add_argument(
        "--disablebatchvectors",
        action="store_true",
        help="Don't compute embeddings in batch for the sections"
    )

    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove references to documents from blob storage and the search index"
    )

    parser.add_argument(
        "--removeall",
        action="store_true",
        help="Remove all blobs from blob storage and documents from the search index"
    )

    # Optional key specification
    parser.add_argument(
        "--searchkey",
        required=False,
        help="Optional. Use this Azure AI Search account key instead of the current user identity"
    )

    parser.add_argument(
        "--storagekey",
        required=False,
        help="Optional. Use this Azure Blob Storage account key instead of the current user identity"
    )

    parser.add_argument(
        "--documentintelligencekey",
        required=False,
        help="Optional. Use this Azure Document Intelligence account key instead of the current user identity"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)])
        logger.setLevel(logging.DEBUG)
    else:
        logging.basicConfig(format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)])
        logger.setLevel(logging.INFO)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(run_dual_indexing(args))
    finally:
        loop.close()
