import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Dialog, DialogType, PrimaryButton, DefaultButton, Stack, Label, TextField, ChoiceGroup, MessageBar, MessageBarType } from "@fluentui/react";

interface Props {
    isOpen: boolean;
    onDismiss: () => void;
    onUpload: (file: File, targetPath: string) => Promise<void>;
    folders: any[];
}

export default function UploadModal({ isOpen, onDismiss, onUpload, folders }: Props) {
    const { t } = useTranslation();
    const [file, setFile] = useState<File | null>(null);
    const [selectedFolder, setSelectedFolder] = useState<string>("");
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.[0]) {
            setFile(e.target.files[0]);
            setError(null);
        }
    };

    const handleUpload = async () => {
        if (!file) {
            setError(t("admin.uploadModal.selectFile"));
            return;
        }

        if (!selectedFolder) {
            setError(t("admin.uploadModal.selectFolder"));
            return;
        }

        try {
            setUploading(true);
            setError(null);
            await onUpload(file, selectedFolder);
            setFile(null);
            setSelectedFolder("");
            onDismiss();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setUploading(false);
        }
    };

    return (
        <Dialog
            hidden={!isOpen}
            onDismiss={onDismiss}
            dialogContentProps={{
                type: DialogType.normal,
                title: t("admin.uploadModal.title"),
            }}
        >
            <Stack gap={16}>
                {error && <MessageBar messageBarType={MessageBarType.error}>{error}</MessageBar>}

                <div>
                    <Label>{t("admin.uploadModal.selectFile")}</Label>
                    <input
                        type="file"
                        onChange={handleFileSelect}
                        accept=".pdf,.docx,.txt,.json,.md,.html,.csv,.pptx,.xlsx,.png,.jpg,.jpeg,.tiff,.bmp,.heic"
                    />
                    {file && <p>{t("admin.uploadModal.selectedFile", { name: file.name })}</p>}
                </div>

                <div>
                    <Label>{t("admin.uploadModal.selectFolder")}</Label>
                    <ChoiceGroup
                        options={folders.map((f) => ({ key: f.path, text: f.name }))}
                        selectedKey={selectedFolder}
                        onChange={(_, option) => setSelectedFolder(option?.key as string)}
                    />
                </div>

                <Stack horizontal gap={8} horizontalAlign="end">
                    <DefaultButton onClick={onDismiss} disabled={uploading} text={t("labels.closeButton")} />
                    <PrimaryButton onClick={handleUpload} disabled={uploading || !file || !selectedFolder} text={t("admin.uploadModal.upload")} />
                </Stack>
            </Stack>
        </Dialog>
    );
}
