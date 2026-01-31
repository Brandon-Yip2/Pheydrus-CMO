import React, { useState, useEffect, useRef, RefObject } from "react";
import { Outlet, NavLink, Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import styles from "./Layout.module.css";

import { useLogin } from "../../authConfig";
import { configApi, IndexesConfig } from "../../api";

import { LoginButton } from "../../components/LoginButton";
import { IconButton } from "@fluentui/react";

const Layout = () => {
    const { t } = useTranslation();
    const [menuOpen, setMenuOpen] = useState(false);
    const [indexes, setIndexes] = useState<IndexesConfig>({});
    const [defaultIndex, setDefaultIndex] = useState<string>("internal");
    const menuRef: RefObject<HTMLDivElement> = useRef(null);
    const location = useLocation();

    const toggleMenu = () => {
        setMenuOpen(!menuOpen);
    };

    const handleClickOutside = (event: MouseEvent) => {
        if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
            setMenuOpen(false);
        }
    };

    useEffect(() => {
        // Load index configuration from backend
        configApi().then(config => {
            if (config.indexes && Object.keys(config.indexes).length > 0) {
                setIndexes(config.indexes);
            } else {
                // Fallback if no indexes from config
                setIndexes({
                    internal: { title: "Private CMO", subtitle: "", navLabel: "Private CMO", icon: "Lock", order: 1 },
                    public: { title: "Public CMO", subtitle: "", navLabel: "Public CMO", icon: "Globe", order: 2 }
                });
            }
            if (config.defaultIndex) {
                setDefaultIndex(config.defaultIndex);
            }
        }).catch(() => {
            // Fallback on error
            setIndexes({
                internal: { title: "Private CMO", subtitle: "", navLabel: "Private CMO", icon: "Lock", order: 1 },
                public: { title: "Public CMO", subtitle: "", navLabel: "Public CMO", icon: "Globe", order: 2 }
            });
        });
    }, []);

    useEffect(() => {
        if (menuOpen) {
            document.addEventListener("mousedown", handleClickOutside);
        } else {
            document.removeEventListener("mousedown", handleClickOutside);
        }
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [menuOpen]);

    // Sort indexes by order and generate nav items
    const sortedIndexes = Object.entries(indexes).sort(([, a], [, b]) => a.order - b.order);

    // Helper to check if a nav link is active
    const isIndexActive = (indexKey: string) => {
        const path = location.pathname;
        if (indexKey === defaultIndex) {
            // Default index is active on "/" or "/chat/{defaultIndex}"
            return path === "/" || path === `/#` || path === `/chat/${indexKey}`;
        }
        return path === `/chat/${indexKey}`;
    };

    return (
        <div className={styles.layout}>
            <header className={styles.header} role={"banner"}>
                <div className={styles.headerContainer} ref={menuRef}>
                    <Link to="/" className={styles.headerTitleContainer}>
                        <h3 className={styles.headerTitle}>{t("headerTitle")}</h3>
                    </Link>
                    <nav>
                        <ul className={`${styles.headerNavList} ${menuOpen ? styles.show : ""}`}>
                            {sortedIndexes.map(([key, config]) => (
                                <li key={key}>
                                    <NavLink
                                        to={key === defaultIndex ? "/" : `/chat/${key}`}
                                        className={() => (isIndexActive(key) ? styles.headerNavPageLinkActive : styles.headerNavPageLink)}
                                        onClick={() => setMenuOpen(false)}
                                    >
                                        {config.navLabel}
                                    </NavLink>
                                </li>
                            ))}
                            <li key="admin">
                                <NavLink
                                    to="/admin"
                                    className={({ isActive }) => (isActive ? styles.headerNavPageLinkActive : styles.headerNavPageLink)}
                                    onClick={() => setMenuOpen(false)}
                                >
                                    {t("admin.navLabel")}
                                </NavLink>
                            </li>
                        </ul>
                    </nav>
                    <div className={styles.loginMenuContainer}>
                        {useLogin && <LoginButton />}
                        <IconButton
                            iconProps={{ iconName: "GlobalNavButton" }}
                            className={styles.menuToggle}
                            onClick={toggleMenu}
                            ariaLabel={t("labels.toggleMenu")}
                        />
                    </div>
                </div>
            </header>

            <main className={styles.main} id="main-content">
                <Outlet />
            </main>
        </div>
    );
};

export default Layout;
