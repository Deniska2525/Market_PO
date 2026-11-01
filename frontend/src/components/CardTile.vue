<template>
  <router-link :to="`/cards/${card.id}`" class="tile">
    <div class="cover" :class="{ placeholder: !card.cover_url }">
      <img v-if="card.cover_url" :src="apiUrl(card.cover_url)" :alt="card.title" loading="lazy">
      <span v-else aria-hidden="true">{{ card.faculty_short_name || initials(card.faculty_name) }}</span>
    </div>

    <div class="body">
      <div class="meta">
        <span class="u-chip">{{ card.faculty_short_name || card.faculty_name }}</span>
        <span v-if="card.readiness" class="u-badge u-badge--info">{{ READINESS_LABELS[card.readiness] }}</span>
        <span v-if="card.status !== 'published'" class="u-badge u-badge--warning">{{ STATUS_LABELS[card.status] }}</span>
      </div>
      <h3>{{ card.title }}</h3>
      <p class="summary">{{ card.summary }}</p>
      <div v-if="card.tags.length" class="u-chips">
        <span v-for="tag in card.tags.slice(0, 4)" :key="tag" class="u-chip">{{ tag }}</span>
      </div>
      <p v-if="reason" class="reason"><strong>Почему подходит:</strong> {{ reason }}</p>
    </div>
  </router-link>
</template>

<script setup>
import { apiUrl } from '../services/university'
import { READINESS_LABELS, STATUS_LABELS, initials } from '../utils/format'

defineProps({
  card: { type: Object, required: true },
  reason: { type: String, default: '' } // пояснение нейросети, почему карточка подходит
})
</script>

<style scoped>
.tile {
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  overflow: hidden;
  text-decoration: none;
  color: inherit;
  transition: transform 0.15s, border-color 0.15s;
}
.tile:hover { transform: translateY(-2px); border-color: var(--primary-color); }

.cover { height: 150px; background: var(--bg-tertiary); overflow: hidden; }
.cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.cover.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--hero-gradient);
  color: var(--on-primary);
  font-size: 2rem;
  font-weight: 700;
}

.body { padding: 1rem; display: flex; flex-direction: column; gap: 0.5rem; flex: 1; }
.meta { display: flex; gap: 0.4rem; flex-wrap: wrap; }
h3 { color: var(--text-primary); font-size: 1.05rem; line-height: 1.3; }
.summary {
  color: var(--text-secondary);
  font-size: 0.92rem;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.reason {
  margin-top: auto;
  padding: 0.6rem 0.8rem;
  background: var(--hover-bg);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 0.88rem;
  line-height: 1.45;
}
</style>
