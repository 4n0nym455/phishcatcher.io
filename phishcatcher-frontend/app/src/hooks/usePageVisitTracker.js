import { useState, useEffect } from 'react';

const STORAGE_KEY = 'phishcatcher_visited_pages';

export function usePageVisitTracker() {
  const [visitedPages, setVisitedPages] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : { terms: false, privacy: false };
  });

  const markPageVisited = (page) => {
    if (page === 'terms' || page === 'privacy') {
      const updated = { ...visitedPages, [page]: true };
      setVisitedPages(updated);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    }
  };

  const hasVisitedBothPages = visitedPages.terms && visitedPages.privacy;

  return { visitedPages, markPageVisited, hasVisitedBothPages };
}
