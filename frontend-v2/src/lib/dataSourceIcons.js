/**
 * Data source name -> icon slug for /data-sources/{slug}.png
 * Used by Dashboard OpenClaw table and Agent Command Center Top Candidates.
 */
export const DATA_SOURCE_ICON_SLUGS = {
  finviz: "finviz",
  whale_flow: "unusual_whales",
  alpaca: "alpaca",
  fred: "fred",
  sec_edgar: "sec_edgar",
  stockgeist: "stockgeist",
  news_api: "news_api",
  discord: "discord",
  twitter: "twitter",
  youtube: "youtube",
};

export function getDataSourceIconSlug(source) {
  if (!source || typeof source !== "string") return null;
  return DATA_SOURCE_ICON_SLUGS[source.toLowerCase()] ?? null;
}
