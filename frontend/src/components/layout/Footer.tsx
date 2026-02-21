import { Shield } from "lucide-react";

const techBadges = ["React", "TypeScript", "Tailwind CSS", "Framer Motion", "Blockchain", "Agentic AI"];

const Footer = () => (
  <footer className="border-t border-border bg-secondary/30 py-12">
    <div className="container mx-auto px-6">
      <div className="flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-trust-green-glow" />
          <span className="font-heading text-lg font-semibold text-foreground">ProofOfCarbon</span>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          {techBadges.map((badge) => (
            <span
              key={badge}
              className="rounded-full border border-border bg-muted/50 px-3 py-1 text-xs text-muted-foreground"
            >
              {badge}
            </span>
          ))}
        </div>
      </div>
      <p className="mt-8 text-center text-sm text-muted-foreground">
        Built for transparency and climate trust. © {new Date().getFullYear()} ProofOfCarbon.
      </p>
    </div>
  </footer>
);

export default Footer;
