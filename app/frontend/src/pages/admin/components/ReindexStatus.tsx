import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Stack, PrimaryButton, DefaultButton, MessageBar, MessageBarType, Spinner, DetailsList, DetailsListLayoutMode, SelectionMode, IColumn } from "@fluentui/react";

import { triggerReindex, listReindexJobs } from "../../../api";

interface Props {
    token: string;
}

interface ReindexJob {
    id: string;
    index: string;
    status: "pending" | "running" | "completed" | "failed";
    started_by: string;
    started_at: string;
    completed_at?: string;
    error?: string;
}

export default function ReindexStatus({ token }: Props) {
    const { t } = useTranslation();
    const [jobs, setJobs] = useState<ReindexJob[]>([]);
    const [loading, setLoading] = useState(true);
    const [reindexing, setReindexing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    useEffect(() => {
        loadJobs();
        const interval = setInterval(loadJobs, 5000); // Poll every 5 seconds
        return () => clearInterval(interval);
    }, [token]);

    const loadJobs = async () => {
        try {
            setError(null);
            const data = await listReindexJobs(token);
            setJobs(data.jobs || []);
            setLoading(false);
        } catch (err: any) {
            setError(err.message);
            setLoading(false);
        }
    };

    const handleReindex = async (indexType: "private" | "public" | "both") => {
        try {
            setReindexing(true);
            setError(null);
            await triggerReindex(token, indexType);
            setSuccess(t("admin.reindexStatus.triggered"));
            setTimeout(() => setSuccess(null), 3000);
            await loadJobs();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setReindexing(false);
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case "completed":
                return { text: "✓", color: "#107c10" };
            case "failed":
                return { text: "✕", color: "#da3b01" };
            case "running":
                return { text: "⟳", color: "#0078d4" };
            default:
                return { text: "○", color: "#605e5c" };
        }
    };

    const columns: IColumn[] = [
        {
            key: "id",
            name: t("admin.reindexStatus.columns.id"),
            fieldName: "id",
            minWidth: 150,
            isResizable: true,
        },
        {
            key: "index",
            name: t("admin.reindexStatus.columns.index"),
            fieldName: "index",
            minWidth: 100,
        },
        {
            key: "status",
            name: t("admin.reindexStatus.columns.status"),
            minWidth: 100,
            onRender: (item: ReindexJob) => {
                const badge = getStatusBadge(item.status);
                return <span style={{ color: badge.color }}>{badge.text} {item.status}</span>;
            },
        },
        {
            key: "started_at",
            name: t("admin.reindexStatus.columns.startedAt"),
            fieldName: "started_at",
            minWidth: 150,
            onRender: (item: ReindexJob) => new Date(item.started_at).toLocaleString(),
        },
        {
            key: "completed_at",
            name: t("admin.reindexStatus.columns.completedAt"),
            fieldName: "completed_at",
            minWidth: 150,
            onRender: (item: ReindexJob) => item.completed_at ? new Date(item.completed_at).toLocaleString() : "-",
        },
    ];

    if (loading) {
        return <Spinner size={6} label={t("admin.loading")} />;
    }

    return (
        <Stack gap={16} style={{ marginTop: "1rem" }}>
            {error && <MessageBar messageBarType={MessageBarType.error}>{error}</MessageBar>}
            {success && <MessageBar messageBarType={MessageBarType.success}>{success}</MessageBar>}

            <Stack horizontal gap={8}>
                <PrimaryButton
                    onClick={() => handleReindex("both")}
                    disabled={reindexing}
                    text={t("admin.reindexStatus.triggerBoth")}
                />
                <DefaultButton
                    onClick={() => handleReindex("private")}
                    disabled={reindexing}
                    text={t("admin.reindexStatus.triggerPrivate")}
                />
                <DefaultButton
                    onClick={() => handleReindex("public")}
                    disabled={reindexing}
                    text={t("admin.reindexStatus.triggerPublic")}
                />
                <DefaultButton onClick={loadJobs} disabled={reindexing} text={t("admin.reindexStatus.refresh")} />
            </Stack>

            <DetailsList
                items={jobs.map((j) => ({ ...j, key: j.id }))}
                columns={columns}
                layoutMode={DetailsListLayoutMode.justified}
                selectionMode={SelectionMode.none}
            />
        </Stack>
    );
}
