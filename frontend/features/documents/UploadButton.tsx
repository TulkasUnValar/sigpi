"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Upload } from "lucide-react";
import { UploadDialog } from "./UploadDialog";
import { canUploadDocuments } from "./permissions";
import { useAuthStore } from "@/store/auth";

export function UploadButton() {
  const roles = useAuthStore((state) => state.roles) || [];
  const t = useTranslations("documents");

  if (!canUploadDocuments(roles)) {
    return null;
  }

  return (
    <UploadDialog>
      <Button>
        <Upload className="mr-2 h-4 w-4" />
        {t("upload.button")}
      </Button>
    </UploadDialog>
  );
}
