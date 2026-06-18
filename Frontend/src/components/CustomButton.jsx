export default function CustomButton({ label, action }) {
    return (
        <button
            onClick={action}
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2 px-4 rounded shadow-lg transition-all"
        >
            {label}
        </button>
    )
}