import { useTranslation } from "react-i18next";
import { DetailsList, DetailsListLayoutMode, SelectionMode, IColumn, Stack, IconButton, Label, Checkbox } from "@fluentui/react";

interface Props {
    folders: any[];
    onFolderIndexChange: (path: string, indexes: string[]) => void;
    onDeleteFile: (path: string) => void;
}

export default function FileTreeView({ folders, onFolderIndexChange, onDeleteFile }: Props) {
    const { t } = useTranslation();

    const columns: IColumn[] = [
        {
            key: "name",
            name: t("admin.fileManager.columns.name"),
            fieldName: "name",
            minWidth: 200,
            isResizable: true,
        },
        {
            key: "path",
            name: t("admin.fileManager.columns.path"),
            fieldName: "path",
            minWidth: 300,
            isResizable: true,
        },
        {
            key: "indexes",
            name: t("admin.fileManager.columns.indexes"),
            minWidth: 150,
            onRender: (item: any) => (
                <Stack horizontal gap={8}>
                    <Checkbox
                        label="Private"
                        checked={item.indexes.includes("private")}
                        onChange={(_, checked) => {
                            const newIndexes = checked
                                ? [...item.indexes, "private"].filter((v, i, a) => a.indexOf(v) === i)
                                : item.indexes.filter((idx: string) => idx !== "private");
                            onFolderIndexChange(item.path, newIndexes);
                        }}
                    />
                    <Checkbox
                        label="Public"
                        checked={item.indexes.includes("public")}
                        onChange={(_, checked) => {
                            const newIndexes = checked
                                ? [...item.indexes, "public"].filter((v, i, a) => a.indexOf(v) === i)
                                : item.indexes.filter((idx: string) => idx !== "public");
                            onFolderIndexChange(item.path, newIndexes);
                        }}
                    />
                </Stack>
            ),
        },
        {
            key: "enabled",
            name: t("admin.fileManager.columns.enabled"),
            fieldName: "enabled",
            minWidth: 80,
            onRender: (item: any) => item.enabled ? "✓" : "✗",
        },
    ];

    const items = folders.map((folder: any) => ({
        ...folder,
        key: folder.path,
    }));

    return (
        <DetailsList
            items={items}
            columns={columns}
            layoutMode={DetailsListLayoutMode.justified}
            selectionMode={SelectionMode.none}
        />
    );
}
