"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useScopingStore } from "@/stores/scoping-store";
import { useI18n } from "@/lib/i18n";

export function AddDimensionDialog() {
  const addExtensionDimension = useScopingStore((s) => s.addExtensionDimension);
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [intent, setIntent] = useState("");

  const canSubmit = title.trim().length > 0;

  function handleSubmit() {
    if (!canSubmit) return;
    addExtensionDimension(title.trim(), intent.trim());
    setTitle("");
    setIntent("");
    setOpen(false);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        render={
          <button
            type="button"
            className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium text-muted-foreground hover:text-foreground border border-dashed border-border hover:border-foreground/40 rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
          />
        }
      >
        <Plus className="h-4 w-4" />
        {t("addDimension")}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle
            className="text-2xl"
            style={{
              fontFamily: "var(--font-display)",
              fontVariationSettings: '"opsz" 144',
            }}
          >
            {t("newDimensionTitle")}
          </DialogTitle>
          <DialogDescription>
            {t("newDimensionDescription")}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="new-dim-title" className="text-sm font-medium">
              {t("sectionTitle")}
              <span className="text-destructive ml-1">*</span>
            </Label>
            <Input
              id="new-dim-title"
              name="new-dim-title"
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("sectionTitlePlaceholder")}
              autoComplete="off"
              spellCheck={false}
              maxLength={40}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new-dim-intent" className="text-sm font-medium">
              {t("intentLabel")}
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                {t("optionalIntentHint")}
              </span>
            </Label>
            <Textarea
              id="new-dim-intent"
              name="new-dim-intent"
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
              placeholder={t("intentPlaceholder")}
              rows={3}
              maxLength={200}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            {t("cancel")}
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {t("add")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
