import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import HeroSection from "@/components/landing/HeroSection";
import ProblemSection from "@/components/landing/ProblemSection";
import SolutionSection from "@/components/landing/SolutionSection";
import TrustStackSection from "@/components/landing/TrustStackSection";
import WorkflowSection from "@/components/landing/WorkflowSection";

const Index = () => (
  <main>
    <Navbar />
    <HeroSection />
    <ProblemSection />
    <SolutionSection />
    <TrustStackSection />
    <WorkflowSection />
    <Footer />
  </main>
);

export default Index;
