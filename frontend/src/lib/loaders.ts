import { apiFetch } from "@/lib/api";
import type { InventoryItem, Page } from "@/lib/types";

/** Fetch every inventory item, respecting the API's maximum page size. */
export async function loadAllInventory() {
  const items: InventoryItem[] = [];
  let page = 1;
  let pages = 1;
  do {
    const data = await apiFetch<Page<InventoryItem>>(
      `/inventory?page=${page}&page_size=100&sort=name&order=asc`,
    );
    items.push(...data.items);
    pages = data.pages;
    page += 1;
  } while (page <= pages);
  return items;
}
