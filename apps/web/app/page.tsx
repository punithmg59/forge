import { Navbar } from "@/components/landing/Navbar";
import { Hero } from "@/components/landing/Hero";
import { ProductValue } from "@/components/landing/ProductValue";
import { WhatForgeDoes } from "@/components/landing/WhatForgeDoes";
import { OperatingLoop } from "@/components/landing/OperatingLoop";
import { FounderControl } from "@/components/landing/FounderControl";
import { SpecializedIntelligence } from "@/components/landing/SpecializedIntelligence";
import { CompanyBrain } from "@/components/landing/CompanyBrain";
import { Differentiation } from "@/components/landing/Differentiation";
import { ProductPreview } from "@/components/landing/ProductPreview";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { TrustSection } from "@/components/landing/TrustSection";
import { FinalCTA } from "@/components/landing/FinalCTA";

export default function HomePage() {
  return (
    <div className="grid-bg relative min-h-screen">
      {/* Background orbs */}
      <div
        className="orb orb-purple"
        style={{ width: 600, height: 600, top: "-150px", left: "-150px" }}
      />
      <div
        className="orb orb-blue"
        style={{ width: 500, height: 500, bottom: "-100px", right: "-100px" }}
      />

      <Navbar />
      <Hero />
      <ProductValue />
      <WhatForgeDoes />
      <OperatingLoop />
      <FounderControl />
      <SpecializedIntelligence />
      <CompanyBrain />
      <Differentiation />
      <ProductPreview />
      <HowItWorks />
      <TrustSection />
      <FinalCTA />
    </div>
  );
}
