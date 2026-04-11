<script setup lang="ts">
/**
 * BlockPropertiesPanel — right-side sidebar that edits the selected block's props.
 * Uses RichTextEditor for "content" props, MediaLibrary for image src, and
 * simple inputs for everything else. Emits `update` with the modified props.
 */
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import type { CmsBlock } from "../../stores/cmsEditor";
import RichTextEditor from "./RichTextEditor.vue";
import MediaLibrary from "./MediaLibrary.vue";
import type { MediaAsset } from "../../lib/media";

const { t } = useI18n();

const props = defineProps<{ block: CmsBlock | null }>();

const emit = defineEmits<{
  (e: "update", key: string, value: any): void;
  (e: "updateAll", props: Record<string, any>): void;
}>();

const pickingImageFor = ref<string | null>(null);

function update(key: string, value: any) {
  emit("update", key, value);
}

function openImagePicker(key: string) {
  pickingImageFor.value = key;
}

function onPickImage(asset: MediaAsset) {
  if (pickingImageFor.value) {
    update(pickingImageFor.value, asset.public_url);
    pickingImageFor.value = null;
  }
}

function addArrayItem(key: string, template: Record<string, any>) {
  if (!props.block) return;
  const arr = [...(props.block.props?.[key] || []), { ...template }];
  update(key, arr);
}

function removeArrayItem(key: string, index: number) {
  if (!props.block) return;
  const arr = [...(props.block.props?.[key] || [])];
  arr.splice(index, 1);
  update(key, arr);
}

function updateArrayItem(key: string, index: number, itemKey: string, val: any) {
  if (!props.block) return;
  const arr = [...(props.block.props?.[key] || [])];
  arr[index] = { ...arr[index], [itemKey]: val };
  update(key, arr);
}

function updateStringArrayItem(key: string, index: number, val: string) {
  if (!props.block) return;
  const arr = [...(props.block.props?.[key] || [])];
  arr[index] = val;
  update(key, arr);
}

function addStringArrayItem(key: string) {
  if (!props.block) return;
  const arr = [...(props.block.props?.[key] || []), ""];
  update(key, arr);
}
</script>

<template>
  <div class="bpp">
    <div v-if="!block" class="bpp-empty">
      <div class="bpp-empty-title">{{ t("cms.components.blockProperties.empty.title") }}</div>
      <div class="bpp-empty-sub">
        {{ t("cms.components.blockProperties.empty.subtitle") }}
      </div>
    </div>

    <template v-else>
      <h4 class="bpp-head">{{ block.type }}</h4>

      <!-- Heading -->
      <template v-if="block.type === 'heading'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.level") }}</span>
          <select
            :value="block.props.level || 'h2'"
            @change="(e:any) => update('level', e.target.value)"
          >
            <option value="h1">H1</option>
            <option value="h2">H2</option>
            <option value="h3">H3</option>
          </select>
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.text") }}</span>
          <input
            :value="block.props.text || ''"
            @input="(e:any) => update('text', e.target.value)"
            type="text"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.align") }}</span>
          <select
            :value="block.props.align || 'left'"
            @change="(e:any) => update('align', e.target.value)"
          >
            <option value="left">{{ t("cms.components.blockProperties.align.left") }}</option>
            <option value="center">{{ t("cms.components.blockProperties.align.center") }}</option>
            <option value="right">{{ t("cms.components.blockProperties.align.right") }}</option>
          </select>
        </label>
      </template>

      <!-- Text -->
      <template v-else-if="block.type === 'text'">
        <div class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.content") }}</span>
          <RichTextEditor
            :model-value="block.props.content || ''"
            @update:model-value="(v:string) => update('content', v)"
          />
        </div>
      </template>

      <!-- Image -->
      <template v-else-if="block.type === 'image'">
        <div class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.source") }}</span>
          <div class="bpp-media-row">
            <input
              :value="block.props.src || ''"
              @input="(e:any) => update('src', e.target.value)"
              type="text"
              :placeholder="t('cms.components.blockProperties.placeholders.imageUrl')"
            />
            <button type="button" @click="openImagePicker('src')">{{ t("cms.components.blockProperties.pick") }}</button>
          </div>
        </div>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.altText") }}</span>
          <input
            :value="block.props.alt || ''"
            @input="(e:any) => update('alt', e.target.value)"
            type="text"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.caption") }}</span>
          <input
            :value="block.props.caption || ''"
            @input="(e:any) => update('caption', e.target.value)"
            type="text"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.maxWidthPx") }}</span>
          <input
            :value="block.props.width ?? 800"
            @input="(e:any) => update('width', Number(e.target.value) || 0)"
            type="number"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.align") }}</span>
          <select
            :value="block.props.align || 'center'"
            @change="(e:any) => update('align', e.target.value)"
          >
            <option value="left">{{ t("cms.components.blockProperties.align.left") }}</option>
            <option value="center">{{ t("cms.components.blockProperties.align.center") }}</option>
            <option value="right">{{ t("cms.components.blockProperties.align.right") }}</option>
          </select>
        </label>
      </template>

      <!-- Hero -->
      <template v-else-if="block.type === 'hero'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.title") }}</span>
          <input
            :value="block.props.title || ''"
            @input="(e:any) => update('title', e.target.value)"
            type="text"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.subtitle") }}</span>
          <textarea
            :value="block.props.subtitle || ''"
            @input="(e:any) => update('subtitle', e.target.value)"
            rows="2"
          ></textarea>
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.backgroundColor") }}</span>
          <input
            :value="block.props.bg_color || '#111110'"
            @input="(e:any) => update('bg_color', e.target.value)"
            type="color"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.ctaText") }}</span>
          <input
            :value="block.props.cta_text || ''"
            @input="(e:any) => update('cta_text', e.target.value)"
            type="text"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.ctaLink") }}</span>
          <input
            :value="block.props.cta_link || ''"
            @input="(e:any) => update('cta_link', e.target.value)"
            type="text"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.secondaryCtaText") }}</span>
          <input
            :value="block.props.cta_secondary_text || ''"
            @input="(e:any) => update('cta_secondary_text', e.target.value)"
            type="text"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.secondaryCtaLink") }}</span>
          <input
            :value="block.props.cta_secondary_link || ''"
            @input="(e:any) => update('cta_secondary_link', e.target.value)"
            type="text"
          />
        </label>
      </template>

      <!-- Feature Grid -->
      <template v-else-if="block.type === 'feature_grid'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.columns") }}</span>
          <input
            :value="block.props.columns ?? 3"
            @input="(e:any) => update('columns', Number(e.target.value) || 3)"
            type="number"
            min="1"
            max="6"
          />
        </label>
        <div class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.items") }}</span>
          <div
            v-for="(item, i) in (block.props.items || [])"
            :key="i"
            class="bpp-array-item"
          >
            <div class="bpp-array-head">
              <span>{{ t("cms.components.blockProperties.arrayLabels.item", { n: i + 1 }) }}</span>
              <button type="button" class="bpp-remove" :title="t('cms.components.blockProperties.remove')" @click="removeArrayItem('items', i)">
                ×
              </button>
            </div>
            <input
              :value="item.icon || ''"
              @input="(e:any) => updateArrayItem('items', i, 'icon', e.target.value)"
              :placeholder="t('cms.components.blockProperties.placeholders.iconEmoji')"
            />
            <input
              :value="item.title || ''"
              @input="(e:any) => updateArrayItem('items', i, 'title', e.target.value)"
              :placeholder="t('cms.components.blockProperties.placeholders.title')"
            />
            <textarea
              :value="item.description || ''"
              @input="(e:any) => updateArrayItem('items', i, 'description', e.target.value)"
              :placeholder="t('cms.components.blockProperties.placeholders.description')"
              rows="2"
            ></textarea>
          </div>
          <button
            type="button"
            class="bpp-add"
            @click="addArrayItem('items', { icon: '', title: '', description: '' })"
          >
            {{ t("cms.components.blockProperties.actions.addItem") }}
          </button>
        </div>
      </template>

      <!-- CTA -->
      <template v-else-if="block.type === 'cta'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.title") }}</span>
          <input
            :value="block.props.title || ''"
            @input="(e:any) => update('title', e.target.value)"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.description") }}</span>
          <textarea
            :value="block.props.description || ''"
            @input="(e:any) => update('description', e.target.value)"
            rows="2"
          ></textarea>
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.buttonText") }}</span>
          <input
            :value="block.props.button_text || ''"
            @input="(e:any) => update('button_text', e.target.value)"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.buttonLink") }}</span>
          <input
            :value="block.props.button_link || ''"
            @input="(e:any) => update('button_link', e.target.value)"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.style") }}</span>
          <select
            :value="block.props.style || 'amber'"
            @change="(e:any) => update('style', e.target.value)"
          >
            <option value="amber">{{ t("cms.components.blockProperties.ctaStyles.amber") }}</option>
            <option value="teal">{{ t("cms.components.blockProperties.ctaStyles.teal") }}</option>
            <option value="dark">{{ t("cms.components.blockProperties.ctaStyles.dark") }}</option>
          </select>
        </label>
      </template>

      <!-- Spacer -->
      <template v-else-if="block.type === 'spacer'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.heightPx") }}</span>
          <input
            :value="block.props.height ?? 40"
            @input="(e:any) => update('height', Number(e.target.value) || 0)"
            type="number"
          />
        </label>
      </template>

      <!-- Divider -->
      <template v-else-if="block.type === 'divider'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.style") }}</span>
          <select
            :value="block.props.style || 'solid'"
            @change="(e:any) => update('style', e.target.value)"
          >
            <option value="solid">{{ t("cms.components.blockProperties.dividerStyles.solid") }}</option>
            <option value="dashed">{{ t("cms.components.blockProperties.dividerStyles.dashed") }}</option>
            <option value="dotted">{{ t("cms.components.blockProperties.dividerStyles.dotted") }}</option>
          </select>
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.widthPercent") }}</span>
          <input
            :value="block.props.width ?? 100"
            @input="(e:any) => update('width', Number(e.target.value) || 100)"
            type="number"
            min="10"
            max="100"
          />
        </label>
      </template>

      <!-- Columns -->
      <template v-else-if="block.type === 'columns'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.count") }}</span>
          <input
            :value="block.props.count ?? 2"
            @input="(e:any) => update('count', Number(e.target.value) || 2)"
            type="number"
            min="1"
            max="6"
          />
        </label>
        <div class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.columns") }}</span>
          <div
            v-for="(item, i) in (block.props.items || [])"
            :key="i"
            class="bpp-array-item"
          >
            <div class="bpp-array-head">
              <span>{{ t("cms.components.blockProperties.arrayLabels.col", { n: i + 1 }) }}</span>
              <button type="button" class="bpp-remove" :title="t('cms.components.blockProperties.remove')" @click="removeArrayItem('items', i)">
                ×
              </button>
            </div>
            <textarea
              :value="item.content || ''"
              @input="(e:any) => updateArrayItem('items', i, 'content', e.target.value)"
              :placeholder="t('cms.components.blockProperties.placeholders.htmlContent')"
              rows="3"
            ></textarea>
          </div>
          <button
            type="button"
            class="bpp-add"
            @click="addArrayItem('items', { content: '' })"
          >
            {{ t("cms.components.blockProperties.actions.addColumn") }}
          </button>
        </div>
      </template>

      <!-- HTML -->
      <template v-else-if="block.type === 'html'">
        <div class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.html") }}</span>
          <textarea
            class="bpp-code"
            :value="block.props.content || ''"
            @input="(e:any) => update('content', e.target.value)"
            rows="10"
            spellcheck="false"
          ></textarea>
        </div>
      </template>

      <!-- Video -->
      <template v-else-if="block.type === 'video'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.url") }}</span>
          <input
            :value="block.props.url || ''"
            @input="(e:any) => update('url', e.target.value)"
            :placeholder="t('cms.components.blockProperties.placeholders.videoUrl')"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.caption") }}</span>
          <input
            :value="block.props.caption || ''"
            @input="(e:any) => update('caption', e.target.value)"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.aspectRatio") }}</span>
          <select
            :value="block.props.aspect_ratio || '16:9'"
            @change="(e:any) => update('aspect_ratio', e.target.value)"
          >
            <option value="16:9">16:9</option>
            <option value="4:3">4:3</option>
            <option value="1:1">1:1</option>
            <option value="21:9">21:9</option>
          </select>
        </label>
        <label class="bpp-check">
          <input
            type="checkbox"
            :checked="!!block.props.autoplay"
            @change="(e:any) => update('autoplay', e.target.checked)"
          />
          <span>{{ t("cms.components.blockProperties.fields.autoplay") }}</span>
        </label>
      </template>

      <!-- Quote -->
      <template v-else-if="block.type === 'quote'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.text") }}</span>
          <textarea
            :value="block.props.text || ''"
            @input="(e:any) => update('text', e.target.value)"
            rows="3"
          ></textarea>
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.author") }}</span>
          <input
            :value="block.props.author || ''"
            @input="(e:any) => update('author', e.target.value)"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.role") }}</span>
          <input
            :value="block.props.role || ''"
            @input="(e:any) => update('role', e.target.value)"
          />
        </label>
        <div class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.avatar") }}</span>
          <div class="bpp-media-row">
            <input
              :value="block.props.avatar || ''"
              @input="(e:any) => update('avatar', e.target.value)"
              :placeholder="t('cms.components.blockProperties.placeholders.imageUrl')"
            />
            <button type="button" @click="openImagePicker('avatar')">{{ t("cms.components.blockProperties.pick") }}</button>
          </div>
        </div>
      </template>

      <!-- Stats -->
      <template v-else-if="block.type === 'stats'">
        <div class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.items") }}</span>
          <div
            v-for="(item, i) in (block.props.items || [])"
            :key="i"
            class="bpp-array-item"
          >
            <div class="bpp-array-head">
              <span>{{ t("cms.components.blockProperties.arrayLabels.stat", { n: i + 1 }) }}</span>
              <button type="button" class="bpp-remove" :title="t('cms.components.blockProperties.remove')" @click="removeArrayItem('items', i)">
                ×
              </button>
            </div>
            <input
              :value="item.value || ''"
              @input="(e:any) => updateArrayItem('items', i, 'value', e.target.value)"
              :placeholder="t('cms.components.blockProperties.placeholders.statValue')"
            />
            <input
              :value="item.label || ''"
              @input="(e:any) => updateArrayItem('items', i, 'label', e.target.value)"
              :placeholder="t('cms.components.blockProperties.placeholders.label')"
            />
            <input
              :value="item.color || '#F5A623'"
              @input="(e:any) => updateArrayItem('items', i, 'color', e.target.value)"
              type="color"
            />
          </div>
          <button
            type="button"
            class="bpp-add"
            @click="addArrayItem('items', { value: '', label: '', color: '#F5A623' })"
          >
            {{ t("cms.components.blockProperties.actions.addStat") }}
          </button>
        </div>
      </template>

      <!-- Button -->
      <template v-else-if="block.type === 'button'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.text") }}</span>
          <input
            :value="block.props.text || ''"
            @input="(e:any) => update('text', e.target.value)"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.link") }}</span>
          <input
            :value="block.props.link || ''"
            @input="(e:any) => update('link', e.target.value)"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.style") }}</span>
          <select
            :value="block.props.style || 'primary'"
            @change="(e:any) => update('style', e.target.value)"
          >
            <option value="primary">{{ t("cms.components.blockProperties.buttonStyles.primary") }}</option>
            <option value="secondary">{{ t("cms.components.blockProperties.buttonStyles.secondary") }}</option>
            <option value="ghost">{{ t("cms.components.blockProperties.buttonStyles.ghost") }}</option>
          </select>
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.size") }}</span>
          <select
            :value="block.props.size || 'md'"
            @change="(e:any) => update('size', e.target.value)"
          >
            <option value="sm">{{ t("cms.components.blockProperties.sizes.small") }}</option>
            <option value="md">{{ t("cms.components.blockProperties.sizes.medium") }}</option>
            <option value="lg">{{ t("cms.components.blockProperties.sizes.large") }}</option>
          </select>
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.align") }}</span>
          <select
            :value="block.props.align || 'left'"
            @change="(e:any) => update('align', e.target.value)"
          >
            <option value="left">{{ t("cms.components.blockProperties.align.left") }}</option>
            <option value="center">{{ t("cms.components.blockProperties.align.center") }}</option>
            <option value="right">{{ t("cms.components.blockProperties.align.right") }}</option>
          </select>
        </label>
      </template>

      <!-- List -->
      <template v-else-if="block.type === 'list'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.type") }}</span>
          <select
            :value="block.props.type || 'ul'"
            @change="(e:any) => update('type', e.target.value)"
          >
            <option value="ul">{{ t("cms.components.blockProperties.listTypes.bullet") }}</option>
            <option value="ol">{{ t("cms.components.blockProperties.listTypes.numbered") }}</option>
          </select>
        </label>
        <div class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.items") }}</span>
          <div
            v-for="(item, i) in (block.props.items || [])"
            :key="i"
            class="bpp-array-item-row"
          >
            <input
              :value="item"
              @input="(e:any) => updateStringArrayItem('items', i, e.target.value)"
            />
            <button type="button" class="bpp-remove" :title="t('cms.components.blockProperties.remove')" @click="removeArrayItem('items', i)">
              ×
            </button>
          </div>
          <button type="button" class="bpp-add" @click="addStringArrayItem('items')">
            {{ t("cms.components.blockProperties.actions.addItem") }}
          </button>
        </div>
      </template>

      <!-- ── HubEx integration blocks ── -->
      <template v-else-if="block.type === 'dashboard_embed'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.dashboardId") }}</span>
          <input
            type="number"
            :value="block.props.dashboard_id || 0"
            @input="(e:any) => update('dashboard_id', Number(e.target.value) || 0)"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.heightPx") }}</span>
          <input
            type="number"
            :value="block.props.height || 600"
            @input="(e:any) => update('height', Number(e.target.value) || 600)"
          />
        </label>
      </template>

      <template v-else-if="block.type === 'variable_value'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.variableKey") }}</span>
          <input
            type="text"
            :value="block.props.key || ''"
            @input="(e:any) => update('key', e.target.value)"
            placeholder="temperature"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.deviceUidOptional") }}</span>
          <input
            type="text"
            :value="block.props.device_uid || ''"
            @input="(e:any) => update('device_uid', e.target.value)"
            placeholder="esp32-01"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.label") }}</span>
          <input
            type="text"
            :value="block.props.label || ''"
            @input="(e:any) => update('label', e.target.value)"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.unit") }}</span>
          <input
            type="text"
            :value="block.props.unit || ''"
            @input="(e:any) => update('unit', e.target.value)"
            placeholder="°C"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.decimals") }}</span>
          <input
            type="number"
            min="0"
            max="6"
            :value="block.props.decimals ?? 1"
            @input="(e:any) => update('decimals', Number(e.target.value))"
          />
        </label>
      </template>

      <template v-else-if="block.type === 'device_card'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.deviceUid") }}</span>
          <input
            type="text"
            :value="block.props.device_uid || ''"
            @input="(e:any) => update('device_uid', e.target.value)"
            placeholder="esp32-01"
          />
        </label>
        <label class="bpp-field bpp-row">
          <input
            type="checkbox"
            :checked="block.props.show_status !== false"
            @change="(e:any) => update('show_status', e.target.checked)"
          />
          <span>{{ t("cms.components.blockProperties.fields.showStatus") }}</span>
        </label>
        <label class="bpp-field bpp-row">
          <input
            type="checkbox"
            :checked="block.props.show_variables !== false"
            @change="(e:any) => update('show_variables', e.target.checked)"
          />
          <span>{{ t("cms.components.blockProperties.fields.showVariables") }}</span>
        </label>
      </template>

      <template v-else-if="block.type === 'device_list'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.filter") }}</span>
          <select
            :value="block.props.filter || 'all'"
            @change="(e:any) => update('filter', e.target.value)"
          >
            <option value="all">{{ t("cms.components.blockProperties.deviceFilter.all") }}</option>
            <option value="online">{{ t("cms.components.blockProperties.deviceFilter.online") }}</option>
            <option value="offline">{{ t("cms.components.blockProperties.deviceFilter.offline") }}</option>
          </select>
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.columns") }}</span>
          <input
            type="number"
            min="1"
            max="6"
            :value="block.props.columns || 3"
            @input="(e:any) => update('columns', Number(e.target.value) || 3)"
          />
        </label>
        <label class="bpp-field bpp-row">
          <input
            type="checkbox"
            :checked="block.props.show_type !== false"
            @change="(e:any) => update('show_type', e.target.checked)"
          />
          <span>{{ t("cms.components.blockProperties.fields.showTypeBadge") }}</span>
        </label>
      </template>

      <template v-else-if="block.type === 'tour_trigger'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.tourId") }}</span>
          <input
            type="text"
            :value="block.props.tour_id || ''"
            @input="(e:any) => update('tour_id', e.target.value)"
            placeholder="getting-started"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.buttonText") }}</span>
          <input
            type="text"
            :value="block.props.button_text || ''"
            @input="(e:any) => update('button_text', e.target.value)"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.style") }}</span>
          <select
            :value="block.props.style || 'primary'"
            @change="(e:any) => update('style', e.target.value)"
          >
            <option value="primary">{{ t("cms.components.blockProperties.buttonStyles.primary") }}</option>
            <option value="secondary">{{ t("cms.components.blockProperties.buttonStyles.secondary") }}</option>
            <option value="ghost">{{ t("cms.components.blockProperties.buttonStyles.ghost") }}</option>
          </select>
        </label>
      </template>

      <template v-else-if="block.type === 'alert_banner'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.severityFilter") }}</span>
          <select
            :value="block.props.severity_filter || 'all'"
            @change="(e:any) => update('severity_filter', e.target.value)"
          >
            <option value="all">{{ t("cms.components.blockProperties.severity.all") }}</option>
            <option value="info">{{ t("cms.components.blockProperties.severity.info") }}</option>
            <option value="warning">{{ t("cms.components.blockProperties.severity.warning") }}</option>
            <option value="critical">{{ t("cms.components.blockProperties.severity.critical") }}</option>
          </select>
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.maxItems") }}</span>
          <input
            type="number"
            min="1"
            max="20"
            :value="block.props.max_items || 3"
            @input="(e:any) => update('max_items', Number(e.target.value) || 3)"
          />
        </label>
        <label class="bpp-field bpp-row">
          <input
            type="checkbox"
            :checked="block.props.auto_hide_if_none !== false"
            @change="(e:any) => update('auto_hide_if_none', e.target.checked)"
          />
          <span>{{ t("cms.components.blockProperties.fields.hideIfNoAlerts") }}</span>
        </label>
      </template>

      <template v-else-if="block.type === 'metric_counter'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.metric") }}</span>
          <select
            :value="block.props.metric || 'devices_online'"
            @change="(e:any) => update('metric', e.target.value)"
          >
            <option value="devices_online">{{ t("cms.components.blockProperties.metrics.devicesOnline") }}</option>
            <option value="devices_total">{{ t("cms.components.blockProperties.metrics.devicesTotal") }}</option>
            <option value="alerts_active">{{ t("cms.components.blockProperties.metrics.alertsActive") }}</option>
            <option value="events_today">{{ t("cms.components.blockProperties.metrics.eventsToday") }}</option>
          </select>
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.label") }}</span>
          <input
            type="text"
            :value="block.props.label || ''"
            @input="(e:any) => update('label', e.target.value)"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.iconEmoji") }}</span>
          <input
            type="text"
            :value="block.props.icon || ''"
            @input="(e:any) => update('icon', e.target.value)"
            placeholder="📡"
          />
        </label>
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.color") }}</span>
          <input
            type="text"
            :value="block.props.color || '#2DD4BF'"
            @input="(e:any) => update('color', e.target.value)"
          />
        </label>
      </template>

      <template v-else-if="block.type === 'automation_status'">
        <label class="bpp-field">
          <span>{{ t("cms.components.blockProperties.fields.automationId") }}</span>
          <input
            type="number"
            :value="block.props.automation_id || 0"
            @input="(e:any) => update('automation_id', Number(e.target.value) || 0)"
          />
        </label>
        <label class="bpp-field bpp-row">
          <input
            type="checkbox"
            :checked="block.props.show_last_fire !== false"
            @change="(e:any) => update('show_last_fire', e.target.checked)"
          />
          <span>{{ t("cms.components.blockProperties.fields.showLastFireTime") }}</span>
        </label>
      </template>

      <!-- Fallback -->
      <template v-else>
        <div class="bpp-fallback">
          {{ t("cms.components.blockProperties.noEditorFor") }} <code>{{ block.type }}</code>
        </div>
      </template>
    </template>

    <!-- Image picker modal -->
    <div
      v-if="pickingImageFor"
      class="bpp-modal"
      @click.self="pickingImageFor = null"
    >
      <div class="bpp-modal-body">
        <MediaLibrary
          picker-mode
          restrict-kind="images"
          @select="onPickImage"
          @close="pickingImageFor = null"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.bpp {
  padding: 14px;
  overflow-y: auto;
  color: #e5e5e5;
}
.bpp-empty {
  padding: 24px 12px;
  text-align: center;
}
.bpp-empty-title {
  font-size: 14px;
  font-weight: 600;
  color: #a1a1aa;
  margin-bottom: 6px;
}
.bpp-empty-sub {
  font-size: 12px;
  color: #71717a;
}
.bpp-head {
  font-size: 13px;
  color: #f5a623;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.bpp-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}
.bpp-field > span {
  font-size: 11px;
  color: #71717a;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.bpp-field input[type="text"],
.bpp-field input[type="number"],
.bpp-field input:not([type]),
.bpp-field select,
.bpp-field textarea {
  background: #0c0c0b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #e5e5e5;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-family: inherit;
  width: 100%;
}
.bpp-field input[type="color"] {
  height: 28px;
  padding: 2px;
  background: #0c0c0b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}
.bpp-code {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
}
.bpp-check {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  font-size: 12px;
  color: #a1a1aa;
}
.bpp-media-row {
  display: flex;
  gap: 4px;
}
.bpp-media-row input {
  flex: 1;
}
.bpp-media-row button {
  background: rgba(245, 166, 35, 0.15);
  color: #f5a623;
  border: 1px solid rgba(245, 166, 35, 0.3);
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
}
.bpp-array-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 8px;
  margin-bottom: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.bpp-array-item input,
.bpp-array-item textarea {
  background: #0c0c0b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #e5e5e5;
  padding: 5px 7px;
  border-radius: 4px;
  font-size: 11px;
  font-family: inherit;
  width: 100%;
}
.bpp-array-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 10px;
  color: #71717a;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}
.bpp-array-item-row {
  display: flex;
  gap: 4px;
  margin-bottom: 4px;
}
.bpp-array-item-row input {
  flex: 1;
  background: #0c0c0b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #e5e5e5;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.bpp-remove {
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #ef4444;
  width: 22px;
  height: 22px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
}
.bpp-remove:hover { background: rgba(239, 68, 68, 0.15); }
.bpp-add {
  background: rgba(45, 212, 191, 0.1);
  color: #2dd4bf;
  border: 1px dashed rgba(45, 212, 191, 0.3);
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
  width: 100%;
  font-size: 11px;
}
.bpp-add:hover { background: rgba(45, 212, 191, 0.2); }
.bpp-fallback {
  padding: 12px;
  color: #71717a;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
}
.bpp-fallback code {
  color: #f5a623;
  font-family: "IBM Plex Mono", monospace;
}
.bpp-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
}
.bpp-modal-body {
  max-width: 900px;
  width: 100%;
  max-height: 85vh;
  overflow: auto;
  background: #0f0f0e;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
}
</style>
