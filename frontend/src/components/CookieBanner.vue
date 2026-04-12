<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const visible = ref(false);

onMounted(() => {
  // Only show if user hasn't accepted yet
  const accepted = localStorage.getItem("hubex_cookies_accepted");
  if (!accepted) {
    visible.value = true;
  }
});

function acceptEssential() {
  localStorage.setItem("hubex_cookies_accepted", "essential");
  visible.value = false;
}

function acceptAll() {
  localStorage.setItem("hubex_cookies_accepted", "all");
  visible.value = false;
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="cookie-banner">
      <div class="cookie-content">
        <p class="cookie-text">
          {{ t('legal.cookies.bannerText') }}
          <router-link to="/datenschutz" class="cookie-link">{{ t('legal.cookies.moreInfo') }}</router-link>
        </p>
        <div class="cookie-actions">
          <button class="cookie-btn essential" @click="acceptEssential">
            {{ t('legal.cookies.essentialOnly') }}
          </button>
          <button class="cookie-btn accept" @click="acceptAll">
            {{ t('legal.cookies.acceptAll') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.cookie-banner {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: rgba(17, 17, 16, 0.95);
  backdrop-filter: blur(12px);
  border-top: 1px solid #333;
  padding: 16px 24px;
}
.cookie-content {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}
.cookie-text {
  font-size: 13px;
  color: #bbb;
  line-height: 1.5;
  flex: 1;
}
.cookie-link {
  color: #F5A623;
  text-decoration: none;
}
.cookie-link:hover { text-decoration: underline; }
.cookie-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}
.cookie-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}
.cookie-btn.essential {
  background: transparent;
  border: 1px solid #444;
  color: #ccc;
}
.cookie-btn.essential:hover {
  border-color: #666;
  color: #fff;
}
.cookie-btn.accept {
  background: #F5A623;
  color: #111;
}
.cookie-btn.accept:hover {
  background: #dda020;
}

@media (max-width: 640px) {
  .cookie-content { flex-direction: column; text-align: center; }
  .cookie-actions { width: 100%; justify-content: center; }
}
</style>
