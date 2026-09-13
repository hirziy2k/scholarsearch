import { Serwist } from "serwist";

declare global {
  interface ServiceWorkerGlobalScope {
    __SW_MANIFEST: (string | { url: string; revision: string })[];
  }
}

const serwist = new Serwist({
  precacheEntries: (self as unknown as ServiceWorkerGlobalScope).__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
});

serwist.addEventListeners();
