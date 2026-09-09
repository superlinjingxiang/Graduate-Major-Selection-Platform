"use client";

import { useMemo, useState } from "react";

import type { DemoProgram } from "../../lib/demo-catalog";

type CatalogSearchProps = Readonly<{
  programs: readonly DemoProgram[];
}>;

export function CatalogSearch({ programs }: CatalogSearchProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const keyword = query.trim().toLocaleLowerCase("zh-CN");
  const suggestions = useMemo(() => {
    if (!keyword) return [];

    return programs
      .filter((program) =>
        [program.institution, program.school, program.title, program.programCode]
          .join(" ")
          .toLocaleLowerCase("zh-CN")
          .includes(keyword),
      )
      .slice(0, 6);
  }, [keyword, programs]);

  const showSuggestions = isOpen && suggestions.length > 0;

  return (
    <search className="catalog-search">
      <form action="/search" className="catalog-search-form" method="get">
        <label className="visually-hidden" htmlFor="catalog-query">
          搜索院校、专业或专业代码
        </label>
        <span className="catalog-search-icon" aria-hidden="true">
          ⌕
        </span>
        <input
          autoComplete="off"
          id="catalog-query"
          name="q"
          onChange={(event) => {
            setQuery(event.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={(event) => {
            if (event.key === "Escape") setIsOpen(false);
          }}
          placeholder="试试“应用心理”或“045400”"
          type="search"
          value={query}
        />
        <button type="submit">搜索</button>
      </form>

      {showSuggestions ? (
        <ul className="catalog-suggestions" id="catalog-suggestions">
          {suggestions.map((program) => (
            <li key={program.slug}>
              <a href={`/programs/${program.slug}`}>
                <span className="suggestion-program">
                  <strong>{program.institution}</strong>
                  <span>{program.title}</span>
                </span>
                <span className="suggestion-meta">
                  {program.programCode} · {program.school}
                </span>
              </a>
            </li>
          ))}
        </ul>
      ) : null}
    </search>
  );
}
