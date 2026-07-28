<script setup lang="ts">
import {
  ElButton,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  type FormInstance,
  type FormRules,
} from "element-plus";
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const formRef = ref<FormInstance>();
const loading = ref(false);

const form = reactive({
  username: "",
  password: "",
});

const rules: FormRules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

async function handleLogin(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await authStore.login(form.username, form.password);
    ElMessage.success("登录成功");
    await router.push("/dashboard");
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "登录失败，请稍后重试";
    ElMessage.error(message);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-brand">SellPilot</div>
        <p class="login-subtitle">AI 跨境电商运营平台</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" autocomplete="username" />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            show-password
            autocomplete="current-password"
          />
        </el-form-item>

        <el-form-item class="submit-item">
          <el-button type="primary" :loading="loading" class="login-button" @click="handleLogin">
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <p class="login-hint">预置账号：admin / admin123</p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  min-height: 100dvh;
  padding: var(--sp-space-6);
  background: #f3f4f6;
}

.login-card {
  width: 100%;
  max-width: 420px;
  padding: var(--sp-space-10) var(--sp-space-8);
  background: #ffffff;
  border-radius: 16px;
  box-shadow:
    0 18px 45px rgba(64, 82, 112, 0.09),
    inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.login-header {
  margin-bottom: var(--sp-space-8);
  text-align: center;
}

.login-brand {
  font-family: var(--sp-font-family);
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--sp-color-primary);
}

.login-subtitle {
  margin: var(--sp-space-2) 0 0;
  font-size: var(--sp-font-sm);
  color: var(--sp-color-text-muted);
}

/* ---- Element Plus form overrides ---- */
:deep(.el-form-item) {
  margin-bottom: var(--sp-space-5);
}

:deep(.el-form-item__label) {
  display: none;
}

:deep(.el-input .el-input__wrapper) {
  border-radius: var(--sp-radius-control);
  box-shadow: 0 0 0 1px var(--sp-border-soft) inset;
  transition: box-shadow var(--sp-transition-fast);
}

:deep(.el-input .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--sp-border-strong) inset;
}

:deep(.el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--sp-color-primary) inset;
}

.submit-item {
  margin-top: var(--sp-space-8);
  margin-bottom: 0;
}

.login-button {
  width: 100%;
  height: 44px;
  font-size: var(--sp-font-md);
  font-weight: 700;
  letter-spacing: 0.08em;
  border-radius: var(--sp-radius-control);
  background: var(--sp-color-primary);
  border-color: var(--sp-color-primary);
}

.login-button:hover,
.login-button:focus {
  background: var(--sp-color-primary-hover);
  border-color: var(--sp-color-primary-hover);
}

.login-hint {
  margin: var(--sp-space-6) 0 0;
  font-size: var(--sp-font-xs);
  color: var(--sp-color-text-muted);
  text-align: center;
}
</style>
