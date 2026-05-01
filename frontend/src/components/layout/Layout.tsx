import { Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div className="flex h-screen bg-[#f9fafb] text-gray-900">
      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>
    </div>
  );
}
