"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const STORAGE_KEY = "gradmatch.demo.compare";
const MAX_COMPARE_ITEMS = 3;

type CompareContextValue = Readonly<{
  slugs: readonly string[];
  toggle: (slug: string) => void;
  clear: () => void;
  isFull: boolean;
}>;

const CompareContext = createContext<CompareContextValue | undefined>(undefined);

function readStoredSlugs(): string[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    if (!Array.isArray(value)) return [];
    return Array.from(
      new Set(value.filter((item): item is string => typeof item === "string")),
    ).slice(0, MAX_COMPARE_ITEMS);
  } catch {
    return [];
  }
}

export function CompareProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [slugs, setSlugs] = useState<readonly string[]>([]);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setSlugs(readStoredSlugs());
    setIsHydrated(true);
  }, []);

  useEffect(() => {
    if (!isHydrated) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(slugs));
    } catch {
      // Browser privacy modes may block storage; in-memory comparison remains available.
    }
  }, [isHydrated, slugs]);

  const toggle = useCallback((slug: string) => {
    setSlugs((current) => {
      if (current.includes(slug)) return current.filter((item) => item !== slug);
      if (current.length >= MAX_COMPARE_ITEMS) return current;
      return [...current, slug];
    });
  }, []);

  const clear = useCallback(() => setSlugs([]), []);
  const value = useMemo<CompareContextValue>(
    () => ({ clear, isFull: slugs.length >= MAX_COMPARE_ITEMS, slugs, toggle }),
    [clear, slugs, toggle],
  );

  return <CompareContext.Provider value={value}>{children}</CompareContext.Provider>;
}

export function useCompare(): CompareContextValue {
  const context = useContext(CompareContext);
  if (!context) throw new Error("useCompare must be used within CompareProvider");
  return context;
}
