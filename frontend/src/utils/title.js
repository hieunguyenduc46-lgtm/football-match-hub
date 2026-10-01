// Set the browser tab title. Makes tabs/bookmarks/history show the right content,
// and helps when the user has many tabs open. (Link previews when sharing use the OG tags in index.html.)
const SUFFIX = 'Football Match Hub'

export function setTitle(name) {
  document.title = name ? `${name} · ${SUFFIX}` : SUFFIX
}
