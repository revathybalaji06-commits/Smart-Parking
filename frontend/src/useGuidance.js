import { useEffect, useState } from "react";

// Find the map position that is `travelled` metres along the route.
function getPosition(route, travelled) {
  const { points, distances } = route;

  for (let index = 1; index < points.length; index++) {
    if (travelled <= distances[index]) {
      const startDistance = distances[index - 1];
      const endDistance = distances[index];
      const distanceInSegment = travelled - startDistance;
      const segmentLength = endDistance - startDistance;
      const fraction = distanceInSegment / segmentLength;

      const startPoint = points[index - 1];
      const endPoint = points[index];
      const x = startPoint[0] + (endPoint[0] - startPoint[0]) * fraction;
      const y = startPoint[1] + (endPoint[1] - startPoint[1]) * fraction;
      return [x, y];
    }
  }

  return points[points.length - 1];
}

export default function useGuidance(route) {
  const [travelled, setTravelled] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const totalDistance = route
    ? route.distances[route.distances.length - 1]
    : 0;
  const steps = route ? route.steps : [];

  // When the driver receives a new route, start at the gate.
  useEffect(() => {
    setTravelled(0);
    setIsPlaying(false);
  }, [route]);

  // Move the dot along the route while guidance is playing.
  useEffect(() => {
    if (!isPlaying) return undefined;

    const timer = setInterval(() => {
      setTravelled((distance) => Math.min(distance + 0.45, totalDistance));
    }, 40);

    return () => clearInterval(timer);
  }, [isPlaying, totalDistance]);

  // Stop the animation when the dot reaches the bay.
  useEffect(() => {
    if (isPlaying && travelled >= totalDistance) {
      setIsPlaying(false);
    }
  }, [isPlaying, travelled, totalDistance]);

  // The current direction is the first step whose end is still ahead.
  let currentStep = steps.findIndex((step) => step.distance > travelled + 0.01);
  if (currentStep === -1) {
    currentStep = steps.length - 1;
  }

  function startOrPause() {
    if (travelled >= totalDistance) {
      setTravelled(0);
    }
    setIsPlaying(!isPlaying);
  }

  function nextStep() {
    if (currentStep < 0) return;
    setIsPlaying(false);
    setTravelled(steps[currentStep].distance);
  }

  function replay() {
    setIsPlaying(false);
    setTravelled(0);
  }

  return {
    steps,
    stepIndex: currentStep,
    playing: isPlaying,
    dot: route ? getPosition(route, travelled) : null,
    startOrPause,
    nextStep,
    replay,
  };
}
