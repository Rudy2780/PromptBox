function ErrorMessage({ message }) {
  if (!message) return null;

  return (
    <div role="alert" className="error-message">
      {message}
    </div>
  );
}

export default ErrorMessage;

