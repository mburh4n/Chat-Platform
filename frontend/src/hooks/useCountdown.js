import { useCallback, useEffect, useState } from "react";

// A seconds counter that ticks down to 0, e.g. for "Resend code in 42s".
// start(n) begins (or restarts) the countdown from n seconds.
export function useCountdown(initialSeconds = 0) {
  const [secondsLeft, setSecondsLeft] = useState(initialSeconds);

  useEffect(() => {
    if (secondsLeft <= 0) {
      return;
    }
    const timerId = setTimeout(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearTimeout(timerId);
  }, [secondsLeft]);

  const start = useCallback((seconds) => setSecondsLeft(seconds), []);

  return [secondsLeft, start];
}
