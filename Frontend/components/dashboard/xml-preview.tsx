"use client";

const defaultXml = `<invoice>
  <invoice_id>INV_1001</invoice_id>
  <issue_date>2025-05-18</issue_date>
  <seller_name>ABC Pvt Ltd</seller_name>
  <buyer_name>XYZ Ltd</buyer_name>
  <tax_category>EXEMPT</tax_category>
  <!-- Missing tax_exemption_reason -->
  <taxable_amount>1000.00</taxable_amount>
  <tax_amount>0.00</tax_amount>
  <payable_amount>1000.00</payable_amount>
</invoice>`;

interface XmlPreviewProps {
  value?: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
}

export default function XmlPreview({ 
  value = defaultXml, 
  onChange,
  readOnly = false 
}: XmlPreviewProps) {
  const lines = value.split('\n');

  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold text-[#07122F]">Invoice XML Preview</h3>
        {!readOnly && (
          <button
            onClick={() => onChange?.(defaultXml)}
            className="text-xs text-indigo-600 hover:text-indigo-700"
          >
            Reset
          </button>
        )}
      </div>
      
      {readOnly ? (
        <div className="overflow-auto rounded-xl border border-slate-200 bg-[#0f172a] p-3">
          <code className="block min-w-[320px] text-xs leading-6 text-slate-200">
            {lines.map((line, idx) => (
              <div key={idx} className="grid grid-cols-[2rem_1fr] gap-3">
                <span className="text-right text-slate-500">{idx + 1}</span>
                <span className="whitespace-pre">{line}</span>
              </div>
            ))}
          </code>
        </div>
      ) : (
        <textarea
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          className="w-full h-64 rounded-xl border border-slate-200 bg-[#0f172a] p-3 text-xs leading-6 text-slate-200 font-mono resize-none focus:outline-none focus:ring-2 focus:ring-indigo-600"
          placeholder="Paste XML content here..."
        />
      )}
    </section>
  );
}