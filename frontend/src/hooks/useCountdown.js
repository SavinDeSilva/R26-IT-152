import { useEffect, useState } from "react";

/** Emergency countdown timer hook — PP1 UX polish. */
export function useCountdown(secondsInitial, active) {
  const [left, setLeft] = useState(secondsInitial);

  useEffect(() => {
    setLeft(secondsInitial);
  }, [secondsInitial, active]);

  useEffect(() => {
    if (!active) return undefined;
    const id = setInterval(() => {
      setLeft((s) => Math.max(0, s - 1));
    }, 1000);
    return () => clearInterval(id);
  }, [active]);

  return left;
}
