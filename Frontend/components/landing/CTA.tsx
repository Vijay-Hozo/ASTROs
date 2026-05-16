export default function CTA() {
  return (
    <section className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-12 mt-12">
      <div className="max-w-6xl mx-auto px-6 text-center">
        <h3 className="text-2xl font-semibold mb-3">Ready to get started?</h3>
        <p className="mb-6 text-white/90">Try the rule builder and validate an invoice in seconds.</p>
        <div className="flex justify-center">
          <button className="px-6 py-3 bg-white/10 rounded-md hover:bg-white/20 transition">Try It Now</button>
        </div>
      </div>
    </section>
  );
}
