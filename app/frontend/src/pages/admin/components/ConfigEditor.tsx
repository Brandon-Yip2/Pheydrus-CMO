import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { TextField, PrimaryButton, DefaultButton, Stack, MessageBar, MessageBarType, Spinner } from "@fluentui/react";

import { getAdminConfig, updateAdminConfig } from "../../../api";

interface Props {
    token: string;
}

export default function ConfigEditor({ token }: Props) {
    const { t } = useTranslation();
    const [config, setConfig] = useState<string>("");
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    useEffect(() => {
        loadConfig();
    }, [token]);

    const loadConfig = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await getAdminConfig(token);
            setConfig(JSON.stringify(data, null, 2));
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            setError(null);
            const parsed = JSON.parse(config);
            await updateAdminConfig(token, parsed);
            setSuccess(t("admin.configEditor.saved"));
            setTimeout(() => setSuccess(null), 3000);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return <Spinner size={6} label={t("admin.loading")} />;
    }

    return (
        <Stack gap={16} style={{ marginTop: "1rem" }}>
            {error && <MessageBar messageBarType={MessageBarType.error}>{error}</MessageBar>}
            {success && <MessageBar messageBarType={MessageBarType.success}>{success}</MessageBar>}

            <TextField
                label={t("admin.configEditor.label")}
                multiline
                rows={20}
                value={config}
                onChange={(_, val) => setConfig(val || "")}
                style={{ fontFamily: "monospace" }}
            />

            <Stack horizontal gap={8}>
                <PrimaryButton onClick={handleSave} disabled={saving} text={t("admin.configEditor.save")} />
                <DefaultButton onClick={loadConfig} disabled={saving} text={t("admin.configEditor.reload")} />
            </Stack>
        </Stack>
    );
}
