import { useEffect, useState } from "react";

// Where is the dot after travelling `distance` metres along the route?
function positionAt(route, distance) {
  const { points, distances } = route;
  for (let i = 1; i < points.length; i++) {
    if (distance <= distances[i]) {
      const part = (distance - distances[i - 1]) / (distances[i] - distances[i - 1]);
      return [
        points[i - 1][0] + (points[i][0] - points[i - 1][0]) * part,
        points[i - 1][1] + (points[i][1] - points[i - 1][1]) * part,
      ];
    }
  }
  return points[points.length - 1];
}

// The moving dot and the step-by-step directions. `route` is null when there is no route.
export default function useGuidance(route) {
  const [progress, setProgress] = useState(0); // metres the dot has travelled
  const [playing, setPlaying] = useState(false);
  const total = route ? route.distances[route.distances.length - 1] : 0;
  const steps = route ? route.steps : [];

  // A new route: start again at the gate
  useEffect(() => {
    setProgress(0);
    setPlaying(false);
  }, [route]);

  // While playing, move the dot a little every 40 ms (about 40 km/h)
  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => setProgress((p) => Math.min(p + 0.45, total)), 40);
    return () => clearInterval(timer);
  }, [playing, total]);

  // Stop at the end
  useEffect(() => {
    if (playing && progress >= total) setPlaying(false);
  }, [progress]);

  // The current step is the first one the dot has not finished yet
  let stepIndex = steps.findIndex((step) => step.distance > progress + 0.01);
  if (stepIndex === -1) stepIndex = steps.length - 1;

  return {
    steps,
    stepIndex,
    playing,
    dot: route ? positionAt(route, progress) : null,
    startOrPause() {
      if (progress >= total) setProgress(0);
      setPlaying(!playing);
    },
    nextStep() {
      setPlaying(false);
      setProgress(steps[stepIndex].distance);
    },
    replay() {
      setPlaying(false);
      setProgress(0);
    },
  };
}
