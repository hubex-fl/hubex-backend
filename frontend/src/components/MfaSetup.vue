<script setup lang="ts">
import { ref, onMounted } from "vue";
import { apiFetch } from "../lib/api";
import { useToastStore } from "../stores/toast";

const toast = useToastStore();

const status = ref<{ totp_enabled: boolean } | null>(null);
const loading = ref(true);

// Setup state
const setupSecret = ref<string | null>(null);
const setupUri = ref<string | null>(null);
const confirmCode = ref("");
const confirming = ref(false);
const recoveryCodes = ref<string[] | null>(null);

const showCodeInput = ref(false);

// Disable state
const disableCode = ref("");
const disabling = ref(false);
const showDisable = ref(false);

async function loadStatus() {
  loading.value = true;
  try {
    status.value = await apiFetch<{ totp_enabled: boolean }>("/api/v1/auth/mfa/status");
  } catch {
    status.value = null;
  } finally {
    loading.value = false;
  }
}

async function startSetup() {
  try {
    const res = await apiFetch<{ secret: string; provisioning_uri: string }>("/api/v1/auth/mfa/totp/setup", {
      method: "POST",
    });
    setupSecret.value = res.secret;
    setupUri.value = res.provisioning_uri;
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : "Setup failed", "error");
  }
}

async function confirmSetup() {
  confirming.value = true;
  try {
    const res = await apiFetch<{ recovery_codes: string[] }>("/api/v1/auth/mfa/totp/confirm", {
      method: "POST",
      body: JSON.stringify({ code: confirmCode.value }),
    });
    recoveryCodes.value = res.recovery_codes;
    toast.addToast("2FA enabled", "success");
    await loadStatus();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : "Invalid code", "error");
  } finally {
    confirming.value = false;
  }
}

async function disableTotp() {
  disabling.value = true;
  try {
    await apiFetch("/api/v1/auth/mfa/totp", {
      method: "DELETE",
      body: JSON.stringify({ code: disableCode.value }),
    });
    toast.addToast("2FA disabled", "success");
    setupSecret.value = null;
    setupUri.value = null;
    recoveryCodes.value = null;
    showDisable.value = false;
    disableCode.value = "";
    await loadStatus();
  } catch (err: unknown) {
    toast.addToast(err instanceof Error ? err.message : "Invalid code", "error");
  } finally {
    disabling.value = false;
  }
}

function closeSetup() {
  setupSecret.value = null;
  setupUri.value = null;
  recoveryCodes.value = null;
  confirmCode.value = "";
  showCodeInput.value = false;
}

onMounted(loadStatus);
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-sm font-semibold text-[var(--text-primary)]">Two-Factor Authentication</h3>
        <p class="text-xs text-[var(--text-muted)]">Add an extra layer of security with TOTP</p>
      </div>
      <span v-if="status?.totp_enabled" class="text-[10px] px-2 py-1 rounded bg-green-500/20 text-green-400 font-medium">Enabled</span>
    </div>

    <div v-if="loading" class="text-xs text-[var(--text-muted)]">Loading...</div>

    <!-- Enabled state -->
    <template v-else-if="status?.totp_enabled">
      <p class="text-xs text-[var(--text-muted)]">Your account is protected with TOTP two-factor authentication.</p>
      <div v-if="!showDisable">
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-medium text-red-400 hover:bg-red-500/10 border border-red-500/30"
          @click="showDisable = true"
        >
          Disable 2FA
        </button>
      </div>
      <div v-else class="flex items-center gap-2">
        <input
          v-model="disableCode"
          class="px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-xs font-mono w-32"
          placeholder="Code"
          maxlength="6"
          @keyup.enter="disableTotp"
        />
        <button
          :disabled="disabling || disableCode.length < 6"
          class="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-500/20 text-red-400 hover:bg-red-500/30 disabled:opacity-50"
          @click="disableTotp"
        >
          {{ disabling ? '...' : 'Confirm Disable' }}
        </button>
        <button class="text-xs text-[var(--text-muted)]" @click="showDisable = false">Cancel</button>
      </div>
    </template>

    <!-- Setup flow -->
    <template v-else>
      <!-- Step 1: Start -->
      <template v-if="!setupSecret">
        <p class="text-xs text-[var(--text-muted)]">Two-factor authentication is not enabled.</p>
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black hover:bg-[var(--primary-hover)]"
          @click="startSetup"
        >
          Enable 2FA
        </button>
      </template>

      <!-- Step 2: Scan QR -->
      <template v-else-if="!recoveryCodes && !showCodeInput">
        <!-- Progress -->
        <div class="flex items-center gap-2 mb-3">
          <span class="h-6 w-6 rounded-full bg-[var(--primary)] text-black text-[10px] font-bold flex items-center justify-center">1</span>
          <span class="text-[10px] text-[var(--text-primary)] font-medium">Scan QR Code</span>
          <span class="flex-1 h-px bg-[var(--border)]" />
          <span class="h-6 w-6 rounded-full bg-[var(--bg-overlay)] text-[var(--text-muted)] text-[10px] font-bold flex items-center justify-center">2</span>
          <span class="text-[10px] text-[var(--text-muted)]">Verify</span>
        </div>
        <div class="rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] p-4 space-y-3">
          <p class="text-xs text-[var(--text-primary)] font-medium">Open your authenticator app and scan this code</p>
          <p class="text-[10px] text-[var(--text-muted)]">Use Google Authenticator, Microsoft Authenticator, Authy, or any TOTP app</p>
          <div class="flex items-center justify-center py-3">
            <div class="bg-white p-3 rounded-lg">
              <img v-if="setupUri" :src="`https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(setupUri)}`" alt="QR Code" class="w-[160px] h-[160px]" />
            </div>
          </div>
          <details class="text-[10px] text-[var(--text-muted)]">
            <summary class="cursor-pointer hover:text-[var(--text-primary)]">Can't scan? Enter manually</summary>
            <code class="mt-1 block text-xs font-mono text-[var(--text-primary)] break-all select-all bg-[var(--bg-base)] p-2 rounded">{{ setupSecret }}</code>
          </details>
          <div class="flex justify-end gap-2">
            <button class="text-xs text-[var(--text-muted)]" @click="closeSetup">Cancel</button>
            <button class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black" @click="showCodeInput = true">I've scanned it</button>
          </div>
        </div>
      </template>

      <!-- Step 3: Enter code -->
      <template v-else-if="!recoveryCodes">
        <!-- Progress -->
        <div class="flex items-center gap-2 mb-3">
          <span class="h-6 w-6 rounded-full bg-[var(--status-ok)] text-white text-[10px] font-bold flex items-center justify-center">1</span>
          <span class="text-[10px] text-[var(--text-muted)]">Scan QR Code</span>
          <span class="flex-1 h-px bg-[var(--border)]" />
          <span class="h-6 w-6 rounded-full bg-[var(--primary)] text-black text-[10px] font-bold flex items-center justify-center">2</span>
          <span class="text-[10px] text-[var(--text-primary)] font-medium">Verify</span>
        </div>
        <div class="rounded-lg border border-[var(--border)] bg-[var(--bg-raised)] p-4 space-y-3">
          <p class="text-xs text-[var(--text-primary)] font-medium">Enter the 6-digit code from your authenticator app</p>
          <div class="flex items-center gap-2">
            <input
              v-model="confirmCode"
              class="px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-base)] text-sm font-mono w-36 text-center tracking-[0.4em]"
              placeholder="000000"
              maxlength="6"
              autofocus
              @keyup.enter="confirmSetup"
            />
            <button
              :disabled="confirming || confirmCode.length < 6"
              class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black disabled:opacity-50"
              @click="confirmSetup"
            >
              {{ confirming ? 'Verifying...' : 'Verify & Enable' }}
            </button>
          </div>
          <div class="flex gap-2">
            <button class="text-[10px] text-[var(--text-muted)] hover:underline" @click="showCodeInput = false">Back to QR</button>
            <button class="text-[10px] text-[var(--text-muted)] hover:underline" @click="closeSetup">Cancel</button>
          </div>
        </div>
      </template>

      <!-- Step 3: Recovery codes -->
      <template v-else>
        <div class="rounded-lg border border-[var(--primary)]/30 bg-[var(--primary)]/5 p-4 space-y-3">
          <p class="text-xs font-medium text-[var(--text-primary)]">Save your recovery codes</p>
          <p class="text-[10px] text-[var(--text-muted)]">Keep these codes safe. If you lose access to your authenticator app, use one of these codes to sign in instead.</p>
          <div class="grid grid-cols-3 sm:grid-cols-4 gap-1.5">
            <code v-for="code in recoveryCodes" :key="code" class="text-xs font-mono text-center py-1.5 rounded bg-[var(--bg-base)] border border-[var(--border)] select-all">{{ code }}</code>
          </div>
          <button
            class="px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--primary)] text-black"
            @click="closeSetup"
          >
            I've saved my codes
          </button>
        </div>
      </template>
    </template>
  </div>
</template>
