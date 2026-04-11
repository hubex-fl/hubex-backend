/**
 * Sprint 5 — shared i18n helpers for backend-seeded feature-flag metadata.
 *
 * The backend (`app/core/features.py`) ships English `name`, `description`
 * and `category` strings on every FeatureFlag row. Until backend i18n
 * lands, we translate them client-side via the locale files:
 *
 *    settings.featureNames.<key>       → translated feature name
 *    settings.featureDescs.<key>       → translated feature description
 *    settings.featureCategory.<slug>   → translated category header
 *
 * Each lookup falls back to the raw English string the backend sent, so
 * it never returns empty.
 *
 * Extracted out of Settings.vue (where the helpers lived as local setup
 * functions since Sprint 3.6) so SetupWizard.vue Step 2 can share them
 * — previously the wizard showed raw English feature names even on DE
 * locale because it had no access to Settings' private helpers.
 */
import { useI18n } from "vue-i18n";

export function useFeatureLabels() {
  const { t } = useI18n();

  function featureName(key: string, raw: string): string {
    const i18nKey = `settings.featureNames.${key}`;
    const translated = t(i18nKey);
    if (translated && translated !== i18nKey) return translated;
    return raw;
  }

  function featureDescription(key: string, raw: string): string {
    const i18nKey = `settings.featureDescs.${key}`;
    const translated = t(i18nKey);
    if (translated && translated !== i18nKey) return translated;
    return raw;
  }

  function featureCategory(slug: string): string {
    const i18nKey = `settings.featureCategory.${slug}`;
    const translated = t(i18nKey);
    if (translated && translated !== i18nKey) return translated;
    return slug;
  }

  return { featureName, featureDescription, featureCategory };
}
