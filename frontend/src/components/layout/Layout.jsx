export default function Layout({ children }) {
  return (
    <div className="min-h-screen flex justify-center font-rubik">
      <main className="flex-1 w-full max-w-[650px] bg-light py-2.5 px-5">
        {children}
      </main>
    </div>
  );
}
