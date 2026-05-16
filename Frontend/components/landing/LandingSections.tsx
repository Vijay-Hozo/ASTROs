import Navbar from "./Navbar";
import Hero from "./Hero";
import RuleInputCard from "./RuleInputCard";
import HowItWorks from "./HowItWorks";
import Features from "./Features";
import CTA from "./CTA";
import Footer from "./Footer";

export default function LandingSections() {
  return (
    <div className="bg-white">
      <Navbar />
      <Hero />
      <RuleInputCard />
      <HowItWorks />
      <Features />
      <CTA />
      <Footer />
    </div>
  );
}
