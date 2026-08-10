import classNames from "classnames";
import { ButtonHTMLAttributes } from "react";

export default function NeutralButton({ children, className, disabled, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={classNames(
        "flex flex-row justify-center items-center gap-2 rounded-md bg-white px-3.5 py-1.5 text-[13px] font-medium text-xinggraph-dark leading-4 border border-xinggraph-border-light",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6510F4]",
        {
          "cursor-pointer hover:bg-xinggraph-hover active:bg-xinggraph-pressed active:border-xinggraph-border": !disabled,
          "cursor-not-allowed opacity-50": disabled,
        },
        className,
      )}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
}
