import { setupWorker } from "msw/browser";

import { handlers } from "@/mocks/handlers";

/** Browser MSW worker for development (NEXT_PUBLIC_API_MOCK=1). */
export const worker = setupWorker(...handlers);