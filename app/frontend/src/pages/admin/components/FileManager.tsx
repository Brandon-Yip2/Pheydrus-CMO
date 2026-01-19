import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { DetailsList, DetailsListLayoutMode, SelectionMode, Stack, PrimaryButton, DefaultButton, MessageBar, MessageBarType, Spinner } from "@fluentui/react";

import styles from "../AdminPortal.module.css";
import { listFilesFlat, updateFolderAssignment, uploadFile as apiUploadFile, deleteFile as apiDeleteFile } from "../../../api";
import FileTreeView from "./FileTreeView";
import UploadModal from "./UploadModal";

interface Props {
    token: string;
}

export default function FileManager({ token }: Props) {
    const { t } = useTranslation();
    const [folders, setFolders] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [selectedFolders, setSelectedFolders] = useState<any[]>([]);
    const [uploadModalOpen, setUploadModalOpen] = useState(false);

    useEffect(() => {
        loadFolders();
    }, [token]);

    const loadFolders = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await listFilesFlat(token);
            setFolders(data.folders || []);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleFolderIndexChange = async (folderPath: string, indexes: string[]) => {
        try {
            setError(null);
            await updateFolderAssignment(token, folderPath, indexes);
            setSuccess(t("admin.fileManager.folderUpdated"));
            await loadFolders();
            setTimeout(() => setSuccess(null), 3000);
        } catch (err: any) {
            setError(err.message);
        }
    };

    const handleUpload = async (file: File, targetPath: string) => {
        try {
            setError(null);
            await apiUploadFile(token, file, targetPath);
            setSuccess(t("admin.fileManager.fileUploaded"));
            setUploadModalOpen(false);
            await loadFolders();
            setTimeout(() => setSuccess(null), 3000);
        } catch (err: any) {
            setError(err.message);
        }
    };

    const handleDeleteFile = async (filePath: string) => {
        if (!confirm(t("admin.fileManager.confirmDelete"))) {
            return;
        }

        try {
            setError(null);
            await apiDeleteFile(token, filePath);
            setSuccess(t("admin.fileManager.fileDeleted"));
            await loadFolders();
            setTimeout(() => setSuccess(null), 3000);
        } catch (err: any) {
            setError(err.message);
        }
    };

    if (loading) {
        return <Spinner size={6} label={t("admin.loading")} />;
    }

    return (
        <Stack gap={16} style={{ marginTop: "1rem" }}>
            {error && <MessageBar messageBarType={MessageBarType.error}>{error}</MessageBar>}
            {success && <MessageBar messageBarType={MessageBarType.success}>{success}</MessageBar>}

            <Stack horizontal gap={8}>
                <PrimaryButton onClick={() => setUploadModalOpen(true)} text={t("admin.fileManager.uploadFile")} />
                <DefaultButton onClick={loadFolders} text={t("admin.fileManager.refresh")} />
            </Stack>

            <div className={styles.container}>
                <FileTreeView
                    folders={folders}
                    onFolderIndexChange={handleFolderIndexChange}
                    onDeleteFile={handleDeleteFile}
                />
            </div>

            <UploadModal
                isOpen={uploadModalOpen}
                onDismiss={() => setUploadModalOpen(false)}
                onUpload={handleUpload}
                folders={folders}
            />
        </Stack>
    );
}
