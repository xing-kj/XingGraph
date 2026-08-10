import classNames from "classnames";
import { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  as?: React.ElementType;
}

export default function IconButton({ as, children, className, ...props }: ButtonProps) {
  const Element = as || "button";

  return (
    <Element
      className={classNames(
        "flex flex-row justify-center items-center gap-2 cursor-pointer rounded-lg bg-transparent p-2 -m-2 text-xinggraph-muted",
        "hover:bg-xinggraph-hover active:bg-xinggraph-pressed",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#6510F4]",
        className,
      )}
      {...props}
    >
      {children}
    </Element>
  );
}
