import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Helmet } from "react-helmet-async";
import { Pivot, PivotItem, MessageBar, MessageBarType, Spinner, SpinnerSize } from "@fluentui/react";
import { useMsal } from "@azure/msal-react";

import styles from "./AdminPortal.module.css";
import { getToken } from "../../authConfig";
import { getAdminInfo } from "../../api";

import FileManager from "./components/FileManager";
import ConfigEditor from "./components/ConfigEditor";
import ReindexStatus from "./components/ReindexStatus";

export function Component() {
    const { t } = useTranslation();
    const { instance } = useMsal();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [adminInfo, setAdminInfo] = useState<any>(null);
    const [token, setToken] = useState<string | null>(null);

    useEffect(() => {
        const initAdmin = async () => {
            try {
                const idToken = await getToken(instance);
                if (!idToken) {
                    setError("Failed to get authentication token");
                    return;
                }
                setToken(idToken);

                const info = await getAdminInfo(idToken);
                setAdminInfo(info);
                setLoading(false);
            } catch (err: any) {
                setError(err.message || "Failed to load admin info");
                setLoading(false);
            }
        };

        initAdmin();
    }, [instance]);

    if (loading) {
        return (
            <div className={styles.container}>
                <Spinner size={SpinnerSize.large} label={t("admin.loading")} />
            </div>
        );
    }

    if (error) {
        return (
            <div className={styles.container}>
                <Helmet>
                    <title>{t("admin.pageTitle")}</title>
                </Helmet>
                <MessageBar messageBarType={MessageBarType.error}>{error}</MessageBar>
            </div>
        );
    }

    if (!token) {
        return (
            <div className={styles.container}>
                <MessageBar messageBarType={MessageBarType.error}>{t("admin.noToken")}</MessageBar>
            </div>
        );
    }

    return (
        <div className={styles.container}>
            <Helmet>
                <title>{t("admin.pageTitle")}</title>
            </Helmet>

            <div className={styles.header}>
                <h1>{t("admin.title")}</h1>
                <p className={styles.userInfo}>
                    {t("admin.loggedInAs")} <strong>{adminInfo?.user?.email}</strong>
                </p>
            </div>

            <Pivot aria-label={t("admin.tabs.label")}>
                <PivotItem headerText={t("admin.tabs.fileManager")}>
                    <FileManager token={token} />
                </PivotItem>

                <PivotItem headerText={t("admin.tabs.configEditor")}>
                    <ConfigEditor token={token} />
                </PivotItem>

                <PivotItem headerText={t("admin.tabs.reindexing")}>
                    <ReindexStatus token={token} />
                </PivotItem>
            </Pivot>
        </div>
    );
}
