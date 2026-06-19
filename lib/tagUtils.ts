export function splitTag(value: string) {
  const [category, ...rest] = String(value || '').split(':');
  return {
    category: rest.length ? category.trim() : 'General',
    name: (rest.length ? rest.join(':') : category).trim()
  };
}

export function getTagCategory(value: string) {
  return splitTag(value).category;
}

export function getTagName(value: string) {
  return splitTag(value).name;
}

export function composeTag(category: string, tag: string) {
  return `${category.trim()}: ${tag.trim()}`;
}

export function formatTagLabel(value: string) {
  const { category, name } = splitTag(value);
  return `${category} · ${name}`;
}

export function tagChipStyle(value: string) {
  const palette = [
    { bg: '#252044', border: '#6f63ff', color: '#c9c5ff' },
    { bg: '#15342a', border: '#38c78b', color: '#a8f0cc' },
    { bg: '#3a2415', border: '#f29b4b', color: '#ffd0a3' },
    { bg: '#3a1825', border: '#f06f9a', color: '#ffc1d3' },
    { bg: '#172d3d', border: '#5bbce9', color: '#b8eaff' }
  ];
  let hash = 0;
  for (const char of getTagCategory(value)) hash = char.charCodeAt(0) + ((hash << 5) - hash);
  const color = palette[Math.abs(hash) % palette.length];
  return { background: color.bg, borderColor: color.border, color: color.color };
}
