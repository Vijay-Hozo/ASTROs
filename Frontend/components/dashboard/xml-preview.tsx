const xmlLines = [
  '<invoice>',
  '  <invoice_id>INV_1001</invoice_id>',
  '  <issue_date>2025-05-18</issue_date>',
  '  <seller_name>ABC Pvt Ltd</seller_name>',
  '  <buyer_name>XYZ Ltd</buyer_name>',
  '  <tax_category>EXEMPT</tax_category>',
  '  <!-- Missing tax_exemption_reason -->',
  '  <taxable_amount>1000.00</taxable_amount>',
  '  <tax_amount>0.00</tax_amount>',
  '  <payable_amount>1000.00</payable_amount>',
  '</invoice>',
];

export default function XmlPreview() {
  return (
    <section className="rounded-2xl border border-slate-200/80 bg-white p-4 shadow-sm">
      <h3 className="mb-3 font-semibold text-[#07122F]">Invoice XML Preview</h3>
      <div className="overflow-auto rounded-xl border border-slate-200 bg-[#0f172a] p-3">
        <code className="block min-w-[320px] text-xs leading-6 text-slate-200">
          {xmlLines.map((line, idx) => (
            <div key={idx} className="grid grid-cols-[2rem_1fr] gap-3">
              <span className="text-right text-slate-500">{idx + 1}</span>
              <span className="whitespace-pre">{line}</span>
            </div>
          ))}
        </code>
      </div>
    </section>
  );
}