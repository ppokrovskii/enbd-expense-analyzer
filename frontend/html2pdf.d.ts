declare module 'html2pdf.js' {
  interface Html2PdfOptions {
    margin?: number | [number, number, number, number];
    filename?: string;
    image?: {
      type?: string;
      quality?: number;
    };
    html2canvas?: {
      scale?: number;
      useCORS?: boolean;
      logging?: boolean;
      letterRendering?: boolean;
    };
    jsPDF?: {
      unit?: string;
      format?: string | [number, number];
      orientation?: 'portrait' | 'landscape';
      compress?: boolean;
    };
    pagebreak?: {
      mode?: string | string[];
      before?: string | string[];
      after?: string | string[];
      avoid?: string | string[];
    };
  }

  interface Html2Pdf {
    set(options: Html2PdfOptions): Html2Pdf;
    from(element: HTMLElement | string): Html2Pdf;
    save(): Promise<void>;
    output(type: string, options?: any): Promise<any>;
    toPdf(): Html2Pdf;
    toContainer(): Html2Pdf;
    toCanvas(): Html2Pdf;
    toImg(): Html2Pdf;
    outputPdf(type?: string, options?: any): any;
    outputImg(type?: string, options?: any): any;
  }

  function html2pdf(): Html2Pdf;
  function html2pdf(element: HTMLElement, opt?: Html2PdfOptions): Html2Pdf;

  export default html2pdf;
}

