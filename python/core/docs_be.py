from python.models.base import get_session

class DocsServiceBE:
    def __init__(self):
        self.session = get_session()

    def save_documentai_response(self, response):
        """
        Save the Document AI response to the database.
        """
        self.session.add(response)
        self.session.commit()
        
    def get_documentai_response(self, response_id):
        """
        Retrieve the Document AI response from the database by ID.
        """
        return self.session.query().filter_by(id=response_id).first()
