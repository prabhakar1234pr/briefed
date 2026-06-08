import { redirect } from "next/navigation";
import { getServerUser } from "@/lib/auth";
import LandingHeader from "@/components/LandingHeader";
import HeroIntro from "@/components/landing/HeroIntro";
import WorkspacePanel from "@/components/landing/WorkspacePanel";
import FeatureScroll from "@/components/landing/FeatureScroll";
import Pricing from "@/components/landing/Pricing";
import DocsCarousel from "@/components/landing/DocsCarousel";
import LandingFooter from "@/components/landing/LandingFooter";
import styles from "./page.module.css";

export default async function LandingPage() {
  const user = await getServerUser();
  if (user) {
    redirect("/home");
  }

  return (
    <div className={styles.page}>
      <LandingHeader />
      <HeroIntro />
      <WorkspacePanel />
      <FeatureScroll />
      <Pricing />
      <DocsCarousel />

      <LandingFooter />
    </div>
  );
}
