import { motion } from "framer-motion";
import { Bot, Lock, Link as LinkIcon } from "lucide-react";

const pillars = [
  {
    icon: Bot,
    title: "Agentic AI",
    subtitle: "Multi-agent reasoning",
    description: "Five specialized agents analyze, cross-reference, and reason about carbon project claims — eliminating single-point-of-failure bias.",
  },
  {
    icon: Lock,
    title: "Federated Learning",
    subtitle: "Privacy-preserving intelligence",
    description: "Fraud detection models learn across organizations without exposing proprietary data, building collective intelligence against greenwashing.",
  },
  {
    icon: LinkIcon,
    title: "Blockchain Audit Trail",
    subtitle: "Immutable on-chain proofs",
    description: "Every verification result is anchored on-chain with a tamper-proof hash, enabling transparent, public auditability for all stakeholders.",
  },
];

const TrustStackSection = () => (
  <section className="section-padding bg-secondary/20">
    <div className="container mx-auto px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="text-center"
      >
        <h2 className="text-3xl font-bold md:text-4xl">
          The <span className="text-gradient-green">Trust Stack</span>
        </h2>
        <p className="mx-auto mt-4 max-w-lg text-muted-foreground">
          Three pillars working in concert to deliver unmatched verification integrity.
        </p>
      </motion.div>

      <div className="mt-16 grid gap-8 md:grid-cols-3">
        {pillars.map((p, i) => (
          <motion.div
            key={p.title}
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: i * 0.15 }}
            className="relative rounded-xl border border-border bg-gradient-card p-8 text-center"
          >
            <div className="mx-auto mb-5 inline-flex rounded-full bg-primary/20 p-4">
              <p.icon className="h-8 w-8 text-trust-green-glow" />
            </div>
            <h3 className="text-lg font-bold">{p.title}</h3>
            <p className="mt-1 text-xs font-medium uppercase tracking-wider text-accent">{p.subtitle}</p>
            <p className="mt-4 text-sm text-muted-foreground leading-relaxed">{p.description}</p>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

export default TrustStackSection;
