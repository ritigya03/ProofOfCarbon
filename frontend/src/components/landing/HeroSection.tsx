import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight, Eye } from "lucide-react";
import { useMemo } from "react";

const particles = Array.from({ length: 40 }, (_, i) => ({
  id: i,
  x: Math.random() * 100,
  y: Math.random() * 100,
  size: Math.random() * 3 + 1,
  duration: Math.random() * 15 + 10,
  delay: Math.random() * 5,
  opacity: Math.random() * 0.4 + 0.1,
}));

const HeroSection = () => (
  <section className="relative min-h-screen flex items-center justify-center bg-gradient-hero overflow-hidden">
    {/* Grid overlay */}
    <div className="absolute inset-0 grid-bg opacity-30" />

    {/* Central green radial glow */}
    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[900px] rounded-full opacity-30"
      style={{ background: "radial-gradient(circle, hsl(116 50% 30% / 0.7) 0%, hsl(116 39% 22% / 0.25) 40%, transparent 70%)" }}
    />
    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full opacity-35 animate-pulse-glow"
      style={{ background: "radial-gradient(circle, hsl(116 50% 40% / 0.5) 0%, transparent 70%)" }}
    />

    {/* Floating particles */}
    {particles.map((p) => (
      <motion.div
        key={p.id}
        className="absolute rounded-full bg-trust-green-glow"
        style={{
          left: `${p.x}%`,
          top: `${p.y}%`,
          width: p.size,
          height: p.size,
          opacity: p.opacity,
        }}
        animate={{
          y: [0, -30, 10, -20, 0],
          x: [0, 10, -10, 5, 0],
          opacity: [p.opacity, p.opacity * 2, p.opacity, p.opacity * 1.5, p.opacity],
        }}
        transition={{
          duration: p.duration,
          repeat: Infinity,
          delay: p.delay,
          ease: "easeInOut",
        }}
      />
    ))}

    {/* Animated glow orbs */}
    <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-primary/10 blur-[120px] animate-pulse-glow" />
    <div className="absolute bottom-1/4 right-1/4 w-72 h-72 rounded-full bg-accent/8 blur-[100px] animate-pulse-glow" style={{ animationDelay: "1.5s" }} />

    <div className="container relative z-10 mx-auto px-6 py-32 text-center">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
      >
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-secondary/50 px-4 py-1.5 text-xs text-muted-foreground backdrop-blur-sm">
          <span className="h-2 w-2 rounded-full bg-trust-green-glow animate-pulse-glow" />
          Powered by Agentic AI + Blockchain
        </div>
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.15 }}
        className="mx-auto max-w-4xl text-4xl font-bold leading-tight sm:text-5xl md:text-6xl lg:text-7xl text-white"
      >
        AI-Verified.{" "}
        <span className="text-gradient-orange">Blockchain-Proven.</span>
        <br />
        <span className="text-gradient-green">Carbon Credits</span> You Can{" "}
        <span className="text-gradient-orange">Trust.</span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.3 }}
        className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground md:text-xl"
      >
        Multi-agent AI analyzes carbon project reports, detects greenwashing, 
        and anchors immutable verification proofs on-chain — so every credit is accountable.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.45 }}
        className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
      >
        <Link
          to="/verify"
          className="group inline-flex items-center gap-2 rounded-lg bg-accent px-6 py-3.5 text-sm font-semibold text-accent-foreground transition-all hover:brightness-110 glow-orange"
        >
          Verify a Carbon Project
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
        </Link>
        <Link
          to="/architecture"
          className="inline-flex items-center gap-2 rounded-lg border border-border bg-secondary/50 px-6 py-3.5 text-sm font-semibold text-foreground transition-all hover:bg-secondary"
        >
          <Eye className="h-4 w-4" />
          View Audit Architecture
        </Link>
      </motion.div>
    </div>
  </section>
);

export default HeroSection;
