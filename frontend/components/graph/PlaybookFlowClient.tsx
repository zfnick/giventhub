"use client";

import dynamic from "next/dynamic";

export const PlaybookFlowClient = dynamic(
  () => import("./PlaybookFlow").then((m) => m.PlaybookFlow),
  { ssr: false }
);
