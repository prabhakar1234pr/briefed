import { SignIn } from "@clerk/nextjs";

export default function AuthPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 py-16 relative z-10" style={{ fontFamily: "var(--font-sans)" }}>
      <SignIn routing="hash" />
    </div>
  );
}
