import { motion } from "framer-motion";
import { AlertTriangle, TrendingDown, ShieldOff } from "lucide-react";

const problems = [
  {
    icon: AlertTriangle,
    title: "Greenwashing at Scale",
    description: "Companies purchase unverified carbon credits to appear sustainable without real environmental impact.",
  },
  {
    icon: TrendingDown,
    title: "Inflated Carbon Claims",
    description: "Many carbon offset projects exaggerate sequestration numbers with no independent verification layer.",
  },
  {
    icon: ShieldOff,
    title: "Zero Audit Transparency",
    description: "Traditional verification is manual, opaque, and susceptible to conflicts of interest and data manipulation.",
  },
];

const ProblemSection = () => (
  <section className="section-padding bg-secondary/20">
    <div className="container mx-auto px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="text-center"
      >
        <h2 className="text-3xl font-bold md:text-4xl">
          The Carbon Credit <span className="text-gradient-orange">Trust Crisis</span>
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
          The voluntary carbon market is projected at $50B+ by 2030 — but it's plagued by fraud.
        </p>
      </motion.div>

      <div className="mt-16 grid gap-6 md:grid-cols-3">
        {problems.map((p, i) => (
          <motion.div
            key={p.title}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: i * 0.15 }}
            className="rounded-xl border border-border bg-gradient-card p-8"
          >
            <div className="mb-4 inline-flex rounded-lg bg-destructive/15 p-3">
              <p.icon className="h-6 w-6 text-highlight-orange" />
            </div>
            <h3 className="text-lg font-semibold">{p.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{p.description}</p>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

export default ProblemSection;
