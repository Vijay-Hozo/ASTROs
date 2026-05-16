import { Code, FileText, GitMerge, ShieldCheck } from "lucide-react";

function FeatureCard({ title, desc, icon: Icon }: { title: string; desc: string; icon: any }) {
  return (
    <div className="bg-secondaryBackground border border-border rounded-2xl p-6 text-left hover:shadow-lg transition transform hover:-translate-y-1">
      <div className="w-12 h-12 rounded-lg bg-primaryBackground flex items-center justify-center mb-4">
        <Icon className="w-5 h-5 text-buttonBlue" />
      </div>
      <h4 className="font-semibold text-textDarkBlue mb-2">{title}</h4>
      <p className="text-textDarkBlue/70 text-sm">{desc}</p>
    </div>
  );
}

export default function Features() {
  const list = [
    { title: "Plain English Rules", desc: "No coding or XSLT knowledge required", icon: FileText },
    { title: "Accurate & Deterministic", desc: "Our templates + logic ensure reliability", icon: GitMerge },
    { title: "Explainable Results", desc: "Clear pass/fail with detailed error messages", icon: ShieldCheck },
    { title: "Enterprise Ready", desc: "Built for compliance, audit and scale", icon: Code },
    { title: "XML/XPath Generation", desc: "Generate XML/XPath validation logic", icon: Code },
    { title: "Compliance Friendly", desc: "Designed for tax & regulatory needs", icon: ShieldCheck },
  ];

  return (
    <section id="features" className="max-w-6xl mx-auto py-12 px-6">
      <h3 className="text-center text-2xl font-semibold mb-8 text-textDarkBlue">Features</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {list.map((f) => (
          <FeatureCard key={f.title} title={f.title} desc={f.desc} icon={f.icon} />
        ))}
      </div>
    </section>
  );
}
