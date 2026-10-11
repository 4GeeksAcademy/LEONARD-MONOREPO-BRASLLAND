"use client";

import { useEffect, useEffectEvent, useState } from "react";

export function useApiData<T>(key: string, load: () => Promise<T>) {
  const [result, setResult] = useState<{ key: string; data?: T; error?: string }>();
  const loadCurrent = useEffectEvent(load);
  useEffect(() => {
    let active = true;
    loadCurrent().then(data => {
      if (active) setResult({ key, data });
    }).catch(error => {
      if (active) setResult({ key, error: error instanceof Error ? error.message : "Unexpected API error." });
    });
    return () => { active = false; };
  }, [key]);
  return result?.key === key ? result : undefined;
}