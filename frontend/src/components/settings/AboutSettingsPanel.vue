<script setup lang="ts">
import { PhGithubLogo } from '@phosphor-icons/vue';
import NetboxLogo from '../NetboxLogo.vue';
import {
  aboutAppName,
  aboutAppId,
  aboutAuthor,
  aboutBuilder,
  aboutCopyright,
  aboutOpenSource,
  aboutRuntimeLabel,
  aboutVersion,
} from '../../aboutMeta';
</script>

<template>
  <div class="about-panel">
    <div class="about-panel__content">
    <div class="about-panel__intro">
      <NetboxLogo :size="28" />
      <div>
        <h3 class="about-panel__title">{{ aboutAppName }}</h3>
      </div>
    </div>

    <p class="about-panel__lead">
      Monitors your local network and internet targets from this machine. History and settings are
      stored locally unless you enable email alerts or run a speed test.
    </p>

    <div class="about-panel__block">
      <h4>What you can monitor</h4>
      <ul class="about-panel__list">
        <li>HTTP/HTTPS, TCP, ICMP, and DNS targets</li>
        <li>Your gateway and Wi‑Fi network against external hosts</li>
        <li>Live status, uptime, and incident history</li>
        <li>Download and upload speed on your network</li>
      </ul>
    </div>

    <dl class="about-panel__meta">
      <div class="about-panel__meta-row">
        <dt>Version</dt>
        <dd>{{ aboutVersion }}</dd>
      </div>
      <div class="about-panel__meta-row">
        <dt>App ID</dt>
        <dd>{{ aboutAppId }}</dd>
      </div>
      <div class="about-panel__meta-row">
        <dt>Builder</dt>
        <dd>{{ aboutBuilder }}</dd>
      </div>
      <div class="about-panel__meta-row">
        <dt>Author</dt>
        <dd>{{ aboutAuthor }}</dd>
      </div>
      <div class="about-panel__meta-row">
        <dt>Runtime</dt>
        <dd>{{ aboutRuntimeLabel() }}</dd>
      </div>
      <div v-if="aboutCopyright" class="about-panel__meta-row">
        <dt>Copyright</dt>
        <dd>{{ aboutCopyright }}</dd>
      </div>
    </dl>
    </div>

    <footer class="about-panel__footer">
      <span v-if="aboutOpenSource" class="about-panel__footer-tag">Open source</span>
      <p class="about-panel__footer-credit">
        Built on Vibes by
        <a href="https://solomonmarvel.com" target="_blank" rel="noopener noreferrer">Marvelous Solomon</a>
        <a
          class="about-panel__footer-github"
          href="https://github.com/solomonmarvel97"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Marvelous Solomon on GitHub"
        >
          <PhGithubLogo class="about-panel__footer-github-icon" weight="fill" aria-hidden="true" />
        </a>
      </p>
    </footer>
  </div>
</template>

<style scoped>
.about-panel {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0;
  min-height: 0;
}

.about-panel__content {
  display: grid;
  flex: 1;
  gap: 16px;
  min-height: 0;
  overflow: auto;
}

.about-panel__intro {
  display: flex;
  align-items: center;
  gap: 12px;
}

.about-panel__title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
  line-height: 1.2;
}

.about-panel__lead {
  margin: 0;
  color: var(--muted);
  font-size: 0.84rem;
  line-height: 1.55;
}

.about-panel__block h4 {
  margin: 0 0 8px;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--faint);
}

.about-panel__list {
  margin: 0;
  padding-left: 1.1rem;
  color: var(--muted);
  font-size: 0.82rem;
  line-height: 1.5;
}

.about-panel__list li + li {
  margin-top: 4px;
}

.about-panel__meta {
  margin: 0;
  display: grid;
  gap: 8px;
}

.about-panel__meta-row {
  display: grid;
  grid-template-columns: 88px 1fr;
  gap: 12px;
  align-items: baseline;
  font-size: 0.82rem;
  line-height: 1.45;
}

.about-panel__meta dt {
  margin: 0;
  color: var(--faint);
}

.about-panel__meta dd {
  margin: 0;
  color: var(--text);
  word-break: break-word;
}

.about-panel__footer {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  box-sizing: border-box;
  height: 42px;
  margin-top: auto;
  padding: 0 16px;
  border-top: 1px solid var(--line-soft);
}

.about-panel__footer-credit {
  margin: 0 0 0 auto;
  color: var(--faint);
  font-size: 0.78rem;
  line-height: 1;
  white-space: nowrap;
}

.about-panel__footer-credit a {
  color: var(--muted);
  text-decoration: none;
}

.about-panel__footer-credit a:hover {
  color: var(--text);
  text-decoration: underline;
}

.about-panel__footer-github {
  display: inline-flex;
  align-items: center;
  margin-left: 0.35rem;
  vertical-align: middle;
  text-decoration: none;
}

.about-panel__footer-github:hover {
  text-decoration: none;
}

.about-panel__footer-github-icon {
  width: 0.9rem;
  height: 0.9rem;
}

.about-panel__footer-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent) 14%, transparent);
  color: var(--accent);
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
</style>
