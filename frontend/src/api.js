// This file contains the browser's requests to the backend API.

async function request(path, method = "GET", body = null) {
  let response;

  try {
    response = await fetch(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body === null ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error("Cannot reach the server. Check your internet connection.");
  }

  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.message || "Something went wrong");
  }
  return result;
}

export function getAvailability() {
  return request("/availability");
}

export function getSlots() {
  return request("/slots");
}

export function getLayout() {
  return request("/layout");
}

export function getReservation(id) {
  return request(`/reservations/${id}`);
}

export function getRoute(id) {
  return request(`/reservations/${id}/route`);
}

export function reserve(plate, vehicleClass) {
  return request("/reserve", "POST", {
    plate,
    vehicle_class: vehicleClass,
  });
}

export function arrive(id) {
  return request(`/reservations/${id}/arrive`, "POST");
}

export function depart(id) {
  return request(`/reservations/${id}/depart`, "POST");
}

export function cancel(id) {
  return request(`/reservations/${id}/cancel`, "POST");
}
