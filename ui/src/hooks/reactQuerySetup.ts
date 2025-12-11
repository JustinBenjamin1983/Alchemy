import { QueryClient } from "@tanstack/react-query";
export enum HTTPMethod {
  GET = "GET",
  POST = "POST",
}

// see alternate here: https://stackoverflow.com/questions/7616461/generate-a-hash-from-string-in-javascript
// export function convertStringToHash(str: string): string {
//   if (str == null || str.length === 0) return "";

//   var hash = 0,
//     i,
//     chr;
//   if (str.length === 0) return hash + "";
//   for (i = 0; i < str.length; i++) {
//     chr = str.charCodeAt(i);
//     hash = (hash << 5) - hash + chr;
//     hash |= 0;
//   }
//   return hash + "";
// }

export enum HTTPStatusCode {
  OK = 200,
}
export const aishopQueryClient = new QueryClient();

const staleTime_15mins: number = 60_000 * 15;
const retryAttempts: number = 0;
const retryDelay = (attemptIndex: number) =>
  Math.min(1000 * 2 ** attemptIndex, 30000);

export const reactQueryDefaults = {
  refetchOnWindowFocus: false,
  staleTime: staleTime_15mins,
  retry: retryAttempts,
  retryDelay: retryDelay,
};
