// Talks to the backend. The address can be changed with VITE_API_URL.
// If it is not set, we call the same server that served this page.
const BASE = import.meta.env.VITE_API_URL || "";

async function call(path, method = "GET", body) {
  let response;
  try {
    response = await fetch(BASE + path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    // no internet, or the server is asleep
    throw new Error("Cannot reach the server. Check your internet connection.");
  }
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || "Something went wrong");
  }
  return data;
}

export const getAvailability = () => call("/availability");
export const getSlots = () => call("/slots");
export const getReservation = (id) => call(`/reservations/${id}`);
export const reserve = (plate, vehicleClass) =>
  call("/reserve", "POST", { plate, vehicle_class: vehicleClass });
export const arrive = (id) => call(`/reservations/${id}/arrive`, "POST");
export const depart = (id) => call(`/reservations/${id}/depart`, "POST");
export const cancel = (id) => call(`/reservations/${id}/cancel`, "POST");

export const getLayout = () => call("/layout");
export const getRoute = (id) => call(`/reservations/${id}/route`);
