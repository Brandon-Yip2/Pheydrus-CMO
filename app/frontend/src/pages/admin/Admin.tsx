import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Helmet } from "react-helmet-async";
import { Dropdown, IDropdownOption, IconButton, Spinner, SpinnerSize } from "@fluentui/react";

import styles from "./Admin.module.css";
import { adminListIndexes, adminListFiles, AdminFileItem, AdminIndexInfo, AdminFilesResponse } from "../../api";

// UI representation of a file/folder item
interface FileTreeItem {
    id: string;
    name: string;
    type: "file" | "folder";
    size?: string;
    modified?: string;
    children?: FileTreeItem[];
    blobPath?: string;
}

function formatFileSize(bytes: number): string {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function formatDate(isoDate: string | null): string {
    if (!isoDate) return "";
    const date = new Date(isoDate);
    return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

// Convert backend response to tree structure
function buildFileTree(data: AdminFilesResponse): FileTreeItem[] {
    const items: FileTreeItem[] = [];

    // Add folders
    const folderNames = Object.keys(data.folders).sort();
    folderNames.forEach((folderName, idx) => {
        const folderData = data.folders[folderName];
        const children: FileTreeItem[] = folderData.files.map((file: AdminFileItem, fileIdx: number) => ({
            id: `folder-${idx}-file-${fileIdx}`,
            name: file.name,
            type: "file" as const,
            size: formatFileSize(file.size),
            modified: formatDate(file.last_modified),
            blobPath: file.path,
        }));

        items.push({
            id: `folder-${idx}`,
            name: folderName,
            type: "folder",
            children,
        });
    });

    // Add root-level files
    data.root_files.forEach((file: AdminFileItem, idx: number) => {
        items.push({
            id: `root-file-${idx}`,
            name: file.name,
            type: "file",
            size: formatFileSize(file.size),
            modified: formatDate(file.last_modified),
            blobPath: file.path,
        });
    });

    return items;
}

export function Component(): JSX.Element {
    const { t } = useTranslation();

    // Index selection state
    const [indexes, setIndexes] = useState<Record<string, AdminIndexInfo>>({});
    const [selectedIndex, setSelectedIndex] = useState<string>("internal");

    // File browser state
    const [fileStructure, setFileStructure] = useState<FileTreeItem[]>([]);
    const [currentPath, setCurrentPath] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Load index configuration from backend
    useEffect(() => {
        adminListIndexes()
            .then(response => {
                setIndexes(response.indexes);
                const keys = Object.keys(response.indexes);
                if (keys.length > 0 && !response.indexes[selectedIndex]) {
                    setSelectedIndex(keys[0]);
                }
            })
            .catch(err => {
                setError(`Failed to load indexes: ${err.message}`);
                setIsLoading(false);
            });
    }, []);

    // Fetch files when index changes
    useEffect(() => {
        if (!selectedIndex) return;
        setIsLoading(true);
        setError(null);
        setCurrentPath([]);

        adminListFiles(selectedIndex)
            .then(response => {
                setFileStructure(buildFileTree(response));
                setIsLoading(false);
            })
            .catch(err => {
                setError(`Failed to load files: ${err.message}`);
                setFileStructure([]);
                setIsLoading(false);
            });
    }, [selectedIndex]);

    // Get current folder contents based on path
    const getCurrentFolderContents = (): FileTreeItem[] => {
        let current = fileStructure;
        for (const pathPart of currentPath) {
            const folder = current.find(item => item.name === pathPart && item.type === "folder");
            if (folder && folder.children) {
                current = folder.children;
            }
        }
        return current;
    };

    // Handle folder navigation
    const navigateToFolder = (folderName: string) => {
        setCurrentPath([...currentPath, folderName]);
    };

    const navigateToBreadcrumb = (index: number) => {
        setCurrentPath(currentPath.slice(0, index));
    };

    // Get file icon based on extension
    const getFileIcon = (fileName: string, isFolder: boolean): string => {
        if (isFolder) return "FolderHorizontal";
        const ext = fileName.split(".").pop()?.toLowerCase();
        switch (ext) {
            case "pdf": return "PDF";
            case "doc":
            case "docx": return "WordDocument";
            case "xls":
            case "xlsx": return "ExcelDocument";
            case "txt":
            case "md":
            case "md5": return "TextDocument";
            case "html": return "FileHTML";
            default: return "Document";
        }
    };

    const getFileIconClass = (fileName: string, isFolder: boolean): string => {
        if (isFolder) return styles.folderIcon;
        const ext = fileName.split(".").pop()?.toLowerCase();
        switch (ext) {
            case "pdf": return styles.fileIconPdf;
            case "doc":
            case "docx": return styles.fileIconDoc;
            case "txt":
            case "md": return styles.fileIconTxt;
            default: return styles.fileIconDefault;
        }
    };

    // Build dropdown options from indexes
    const indexOptions: IDropdownOption[] = Object.entries(indexes)
        .sort(([, a], [, b]) => a.display.order - b.display.order)
        .map(([key, config]) => ({
            key,
            text: config.display.title
        }));

    const currentContents = getCurrentFolderContents();
    const selectedIndexConfig = indexes[selectedIndex];

    // Count total files across all folders
    const totalFiles = fileStructure.reduce((acc, item) => {
        if (item.type === "folder") return acc + (item.children?.length || 0);
        return acc + 1;
    }, 0);

    return (
        <div className={styles.container}>
            <Helmet>
                <title>{t("admin.pageTitle")}</title>
            </Helmet>

            {/* Header */}
            <div className={styles.header}>
                <div>
                    <h1 className={styles.title}>{t("admin.title")}</h1>
                    <p className={styles.subtitle}>{t("admin.subtitle")}</p>
                </div>
            </div>

            {/* Controls Row */}
            <div className={styles.controlsRow}>
                <div className={styles.dropdownContainer}>
                    <span className={styles.dropdownLabel}>{t("admin.selectIndex")}:</span>
                    <Dropdown
                        className={styles.dropdown}
                        selectedKey={selectedIndex}
                        options={indexOptions}
                        onChange={(_, option) => option && setSelectedIndex(option.key as string)}
                        placeholder={t("admin.selectIndexPlaceholder")}
                    />
                </div>
            </div>

            {/* Index Info */}
            {selectedIndexConfig && (
                <div className={styles.indexInfo}>
                    <div className={styles.indexInfoRow}>
                        <span className={styles.indexInfoLabel}>{t("admin.indexName")}:</span>
                        <span className={styles.indexInfoValue}>{selectedIndexConfig.name}</span>
                    </div>
                    <div className={styles.indexInfoRow}>
                        <span className={styles.indexInfoLabel}>{t("admin.description")}:</span>
                        <span className={styles.indexInfoValue}>{selectedIndexConfig.description}</span>
                    </div>
                    <div className={styles.indexInfoRow}>
                        <span className={styles.indexInfoLabel}>{t("admin.totalFolders")}:</span>
                        <span className={styles.indexInfoValue}>
                            {fileStructure.filter(i => i.type === "folder").length} folders, {totalFiles} files
                        </span>
                    </div>
                    <div className={styles.indexInfoRow}>
                        <span className={styles.indexInfoLabel}>Included folders:</span>
                        <span className={styles.indexInfoValue}>
                            {selectedIndexConfig.folders[0] === "*" ? "All folders" : selectedIndexConfig.folders.join(", ")}
                        </span>
                    </div>
                </div>
            )}

            {/* File Manager */}
            <div className={styles.fileManagerContainer}>
                <div className={styles.fileManagerHeader}>
                    <div className={styles.fileManagerTitle}>
                        <IconButton iconProps={{ iconName: "FabricFolder" }} />
                        <span>{t("admin.fileManager")}</span>
                    </div>
                </div>

                {/* Breadcrumb */}
                <div className={styles.breadcrumb}>
                    <span
                        className={currentPath.length > 0 ? styles.breadcrumbItem : styles.breadcrumbCurrent}
                        onClick={() => currentPath.length > 0 && navigateToBreadcrumb(0)}
                    >
                        {selectedIndexConfig?.display.title || "Root"}
                    </span>
                    {currentPath.map((pathPart, index) => (
                        <span key={index}>
                            <span className={styles.breadcrumbSeparator}>/</span>
                            <span
                                className={index === currentPath.length - 1 ? styles.breadcrumbCurrent : styles.breadcrumbItem}
                                onClick={() => index < currentPath.length - 1 && navigateToBreadcrumb(index + 1)}
                            >
                                {pathPart}
                            </span>
                        </span>
                    ))}
                </div>

                {/* Loading state */}
                {isLoading && (
                    <div className={styles.emptyState}>
                        <Spinner size={SpinnerSize.large} label="Loading files from blob storage..." />
                    </div>
                )}

                {/* Error state */}
                {error && !isLoading && (
                    <div className={styles.emptyState}>
                        <p className={styles.emptyStateText} style={{ color: "#a80000" }}>{error}</p>
                    </div>
                )}

                {/* File List */}
                {!isLoading && !error && currentContents.length > 0 && (
                    <ul className={styles.fileList}>
                        {currentContents.map(item => (
                            <li
                                key={item.id}
                                className={styles.fileItem}
                                onClick={() => item.type === "folder" ? navigateToFolder(item.name) : undefined}
                            >
                                <div className={`${styles.fileIcon} ${getFileIconClass(item.name, item.type === "folder")}`}>
                                    <IconButton
                                        iconProps={{ iconName: getFileIcon(item.name, item.type === "folder") }}
                                        styles={{ root: { color: "inherit" } }}
                                    />
                                </div>
                                <div className={styles.fileInfo}>
                                    <div className={styles.fileName}>{item.name}</div>
                                    <div className={styles.fileMeta}>
                                        {item.type === "folder"
                                            ? `${item.children?.length || 0} files`
                                            : `${item.size} ${item.modified ? `- ${item.modified}` : ""}`
                                        }
                                    </div>
                                </div>
                                {item.type === "folder" && (
                                    <div className={styles.fileActions} style={{ opacity: 1 }}>
                                        <IconButton
                                            iconProps={{ iconName: "ChevronRight" }}
                                            title={t("admin.openFolder")}
                                        />
                                    </div>
                                )}
                            </li>
                        ))}
                    </ul>
                )}

                {/* Empty state */}
                {!isLoading && !error && currentContents.length === 0 && (
                    <div className={styles.emptyState}>
                        <p className={styles.emptyStateText}>{t("admin.emptyFolder")}</p>
                    </div>
                )}

                {/* Footer */}
                {!isLoading && !error && (
                    <div className={styles.footer}>
                        <div className={styles.footerInfo}>
                            {currentContents.length} {t("admin.items")} - {currentContents.filter(i => i.type === "folder").length} {t("admin.folders")}, {currentContents.filter(i => i.type === "file").length} {t("admin.files")}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
