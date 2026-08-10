import classNames from "classnames"
import { InputHTMLAttributes } from "react"

export default function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={classNames(
        "block w-full rounded-lg bg-white px-3.5 h-10 text-sm text-xinggraph-body",
        "border border-xinggraph-border",
        "placeholder:text-xinggraph-placeholder",
        "hover:bg-xinggraph-hover",
        "focus:border-[#6510F4] focus:border-2 focus:shadow-[0_0_0_3px_rgba(188,155,255,0.10)] focus:outline-none",
        "disabled:bg-xinggraph-disabled disabled:text-xinggraph-placeholder disabled:cursor-not-allowed",
        className,
      )}
      {...props}
    />
  )
}
