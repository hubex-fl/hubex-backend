<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const visible = ref(false);

onMounted(() => {
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
    <div v-if="visible" class="hbx-consent-strip">
      <div class="hbx-consent-inner">
        <p class="hbx-consent-msg">
          {{ t('legal.cookies.bannerText') }}
          <router-link to="/datenschutz" class="hbx-consent-link">{{ t('legal.cookies.moreInfo') }}</router-link>
        </p>
        <div class="hbx-consent-btns">
          <button class="hbx-consent-btn hbx-essential" @click="acceptEssential">
            {{ t('legal.cookies.essentialOnly') }}
          </button>
          <button class="hbx-consent-btn hbx-accept" @click="acceptAll">
            {{ t('legal.cookies.acceptAll') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.hbx-consent-strip {
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
.hbx-consent-inner {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}
.hbx-consent-msg {
  font-size: 13px;
  color: #bbb;
  line-height: 1.5;
  flex: 1;
}
.hbx-consent-link {
  color: #F5A623;
  text-decoration: none;
}
.hbx-consent-link:hover { text-decoration: underline; }
.hbx-consent-btns {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}
.hbx-consent-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}
.hbx-essential {
  background: transparent;
  border: 1px solid #444;
  color: #ccc;
}
.hbx-essential:hover {
  border-color: #666;
  color: #fff;
}
.hbx-accept {
  background: #F5A623;
  color: #111;
}
.hbx-accept:hover {
  background: #dda020;
}

@media (max-width: 640px) {
  .hbx-consent-inner { flex-direction: column; text-align: center; }
  .hbx-consent-btns { width: 100%; justify-content: center; }
}
</style>
