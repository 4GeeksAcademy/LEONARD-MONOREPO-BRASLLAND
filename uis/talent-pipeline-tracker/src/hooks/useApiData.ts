"use client";

import { useEffect, useEffectEvent, useState } from "react";

export function useApiData<T>(key: string, load: () => Promise<T>) {
  const [result, setResult] = useState<{ key: string; attempt: number; data?: T; error?: string }>();
  const [attempt, setAttempt] = useState(0);
  const loadCurrent = useEffectEvent(load);
  useEffect(() => {
    let active = true;
    async function loadData() {
      try {
        const data = await loadCurrent();
        if (active) setResult({ key, attempt, data });
      } catch {
        if (active) setResult({ key, attempt, error: "We couldn't load this information. Please try again." });
      } finally {
        if (active) {
          setResult(current => current?.key === key && current.attempt === attempt
            ? current
            : { key, attempt, error: "We couldn't load this information. Please try again." });
        }
      }
    }
    void loadData();
    return () => { active = false; };
  }, [key, attempt]);
  const current = result?.key === key && result.attempt === attempt ? result : undefined;
  return {
    data: current?.data,
    error: current?.error,
    isLoading: !current,
    retry: () => setAttempt(value => value + 1),
  };
}